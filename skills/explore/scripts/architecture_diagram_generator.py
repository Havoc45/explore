#!/usr/bin/env python3
"""
Architecture Diagram Generator

Generates architecture diagrams from project structure in multiple formats:
- Mermaid (default)
- PlantUML
- ASCII

Supports diagram types:
- component: Shows modules and their relationships
- layer: Shows architectural layers
- deployment: Shows deployment topology
"""

import os
import sys
import json
import argparse
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict


class ProjectScanner:
    """Scans project structure to detect components and relationships."""

    # Common architectural layer patterns
    LAYER_PATTERNS = {
        'presentation': ['controller', 'handler', 'view', 'page', 'component', 'ui'],
        'api': ['api', 'route', 'endpoint', 'rest', 'graphql'],
        'business': ['service', 'usecase', 'domain', 'logic', 'core'],
        'data': ['repository', 'dao', 'model', 'entity', 'schema', 'migration'],
        'infrastructure': ['config', 'util', 'helper', 'middleware', 'plugin'],
    }

    IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                   'dist', 'build', '.next', '.nuxt', 'coverage', '.pytest_cache'}

    # Technologies identified by a source-file *extension*.  Matched against
    # ``Path.suffix`` exactly: react used to list the bare pattern ``jsx``,
    # which the former ``*{pattern}*`` glob matched against any file name
    # merely containing those letters.
    TECH_EXTENSIONS = {
        'react': ('.jsx', '.tsx'),
        'vue': ('.vue',),
    }

    # Technologies identified by a package-manifest dependency.
    TECH_DEPENDENCIES = {
        'react': {'react', 'react-dom', 'react-native'},
        'vue': {'vue', 'nuxt'},
        'node': {'express', 'fastify'},
    }

    # File patterns for different technologies, matched against file names
    # except for ``k8s``, which is matched as an exact directory name.
    # ``package.json`` is a *node* signature only — listing it under react made
    # every Node project a React project.
    TECH_PATTERNS = {
        'vue': ['nuxt.config'],
        'angular': ['component.ts', 'module.ts', 'angular.json'],
        'node': ['package.json'],
        'python': ['requirements.txt', 'pyproject.toml', 'setup.py'],
        'go': ['go.mod', 'go.sum'],
        'rust': ['Cargo.toml'],
        'java': ['pom.xml', 'build.gradle'],
        'docker': ['Dockerfile', 'docker-compose'],
        'kubernetes': ['deployment.yaml', 'service.yaml', 'k8s'],
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.components: Dict[str, Dict] = {}
        self.relationships: List[Tuple[str, str, str]] = []  # (from, to, type)
        self.layers: Dict[str, List[str]] = defaultdict(list)
        self.technologies: Set[str] = set()
        self.external_deps: Set[str] = set()
        # component name -> normalized top-level names its files import.
        # Kept beside the raw ``imports`` list (which stays verbatim in the
        # JSON output) because resolving a relative import needs the path of
        # the file it appeared in.
        self._import_targets: Dict[str, Set[str]] = defaultdict(set)
        self._package_deps: Set[str] = set()

    def scan(self) -> Dict:
        """Scan the project and return structure information."""
        self._scan_directories()
        self._detect_technologies()
        self._detect_relationships()
        self._classify_layers()

        return {
            'components': self.components,
            'relationships': self.relationships,
            'layers': dict(self.layers),
            'technologies': list(self.technologies),
            'external_deps': list(self.external_deps),
        }

    def _scan_directories(self):
        """Scan directory structure for components."""
        ignore_dirs = self.IGNORE_DIRS

        for item in self.project_path.iterdir():
            if item.is_dir() and item.name not in ignore_dirs and not item.name.startswith('.'):
                component_info = self._analyze_directory(item)
                if component_info['files'] > 0:
                    self.components[item.name] = component_info

    def _analyze_directory(self, dir_path: Path) -> Dict:
        """Analyze a directory to understand its role."""
        code_exts = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.java', '.vue'}
        code_files = []
        try:
            for f in dir_path.rglob('*'):
                try:
                    if f.is_file() and f.suffix in code_exts:
                        code_files.append(f)
                except OSError:
                    pass
        except OSError:
            pass

        # Count imports/dependencies within the directory
        imports = set()
        for f in code_files[:50]:  # Limit to avoid large projects
            file_imports = self._extract_imports(f)
            imports.update(file_imports)
            for imp in file_imports:
                target = self._import_target_key(imp, f)
                if target:
                    self._import_targets[dir_path.name].add(target)

        return {
            'path': str(dir_path.relative_to(self.project_path)),
            'files': len(code_files),
            'imports': list(imports)[:20],  # Top 20 imports
            'type': self._guess_component_type(dir_path.name),
        }

    def _extract_imports(self, file_path: Path) -> Set[str]:
        """Extract import statements from a file."""
        imports = set()
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            suffix = file_path.suffix.lower()

            if suffix == '.py':
                py_imports = re.findall(
                    r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE)
                imports.update(py_imports)
            elif suffix in {'.js', '.jsx', '.ts', '.tsx', '.vue'}:
                es_imports = re.findall(
                    r'(?:import|export)\s+[^\'"\n;]*?from\s*[\'"]([^\'"]+)[\'"]',
                    content)
                imports.update(es_imports)
                side_effect_imports = re.findall(
                    r'(?:import|require)\s*\(?[\'"]([^\'"\s]+)[\'"]', content)
                imports.update(side_effect_imports)
            elif suffix == '.java':
                java_imports = re.findall(
                    r'^import\s+(?:static\s+)?([\w.]+)', content, re.MULTILINE)
                imports.update(java_imports)
            elif suffix == '.go':
                go_imports = re.findall(
                    r'import\s+(?:\(\s*)?["\']([^"\']+)["\']', content)
                imports.update(go_imports)

        except Exception:
            pass

        return imports

    def _import_target_key(self, imp: str, source_file: Path) -> Optional[str]:
        """Normalized top-level name an import refers to, or ``None``.

        Relative specifiers are resolved *lexically* against the importing file
        and mapped back to the top-level directory they land in; one that
        escapes the project root is external.  Everything else reduces to its
        first path segment (and, for dotted module paths, the part before the
        first dot).  Callers compare the result against component names
        **exactly** — a miss means "external", never a guess.  The previous
        substring test let ``rapidjson`` match a component named ``api`` and
        ``happy`` match ``app``, fabricating edges.
        """
        spec = imp.strip().replace('\\', '/')
        if not spec:
            return None

        if spec.startswith('.'):
            resolved = os.path.normpath(os.path.join(str(source_file.parent), spec))
            try:
                rel = Path(resolved).relative_to(self.project_path)
            except ValueError:
                return None  # climbs out of the project -> external
            return rel.parts[0].lower() if rel.parts else None

        if spec.startswith('@/') or spec.startswith('~/'):
            spec = spec[2:]

        return spec.split('/')[0].split('.')[0].strip().lower() or None

    def _guess_component_type(self, name: str) -> str:
        """Guess component type from directory name."""
        name_lower = name.lower()
        for layer, patterns in self.LAYER_PATTERNS.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return layer
        return 'unknown'

    def _detect_technologies(self):
        """Detect technologies used in the project."""
        prefix_patterns = {
            'nuxt.config', 'docker-compose', 'Dockerfile', 'build.gradle',
        }
        suffix_patterns = {
            'component.ts', 'module.ts', 'deployment.yaml', 'service.yaml',
        }
        directory_patterns = {'k8s'}

        for path in self.project_path.rglob('*'):
            name = path.name
            is_file = path.is_file()
            is_dir = path.is_dir()
            for tech, patterns in self.TECH_PATTERNS.items():
                for pattern in patterns:
                    if pattern in directory_patterns:
                        matched = is_dir and name == pattern
                    elif pattern in prefix_patterns:
                        matched = is_file and name.startswith(pattern)
                    elif pattern in suffix_patterns:
                        matched = is_file and name.endswith(pattern)
                    else:
                        matched = is_file and name == pattern
                    if matched:
                        self.technologies.add(tech)
                        break

        self._detect_technologies_by_extension()

        # Detect external dependencies from package files
        self._parse_package_json()
        self._parse_requirements_txt()
        self._parse_go_mod()

        self._detect_technologies_by_dependency()

    def _detect_technologies_by_extension(self):
        """Mark technologies whose signature is a source-file extension.

        The extension must match ``Path.suffix`` exactly, and vendored trees
        are skipped — otherwise a single ``.tsx`` shipped inside
        ``node_modules`` would relabel the whole project.
        """
        for tech, extensions in self.TECH_EXTENSIONS.items():
            for ext in extensions:
                for path in self.project_path.rglob(f'*{ext}'):
                    if path.suffix != ext or not path.is_file():
                        continue
                    try:
                        rel_parts = path.relative_to(self.project_path).parts
                    except ValueError:
                        continue
                    if any(part in self.IGNORE_DIRS for part in rel_parts):
                        continue
                    self.technologies.add(tech)
                    break
                if tech in self.technologies:
                    break

    def _detect_technologies_by_dependency(self):
        """Mark technologies declared as a dependency in package.json."""
        for tech, names in self.TECH_DEPENDENCIES.items():
            if self._package_deps & names:
                self.technologies.add(tech)

    def _parse_package_json(self):
        """Parse package.json for dependencies."""
        pkg_path = self.project_path / 'package.json'
        if pkg_path.exists():
            try:
                data = json.loads(pkg_path.read_text())
                for key in ('dependencies', 'devDependencies', 'peerDependencies'):
                    section = data.get(key)
                    if isinstance(section, dict):
                        self._package_deps.update(section.keys())
                deps = list(data.get('dependencies', {}).keys())[:10]
                self.external_deps.update(deps)
            except Exception:
                pass

    def _parse_requirements_txt(self):
        """Parse requirements.txt for dependencies."""
        req_path = self.project_path / 'requirements.txt'
        if req_path.exists():
            try:
                content = req_path.read_text()
                deps = re.findall(r'^([a-zA-Z0-9_-]+)', content, re.MULTILINE)[:10]
                self.external_deps.update(deps)
            except Exception:
                pass

    def _parse_go_mod(self):
        """Parse go.mod for dependencies."""
        mod_path = self.project_path / 'go.mod'
        if mod_path.exists():
            try:
                content = mod_path.read_text()
                deps = re.findall(r'^\s+([^\s]+)\s+v', content, re.MULTILINE)[:10]
                self.external_deps.update([d.split('/')[-1] for d in deps])
            except Exception:
                pass

    def _detect_relationships(self):
        """Detect relationships between components.

        An import creates an edge only when its normalized top-level name
        equals a component name.  Targets are walked in sorted order so the
        edge list does not depend on set iteration order.
        """
        components_by_key: Dict[str, List[str]] = defaultdict(list)
        for name in self.components:
            components_by_key[name.strip().lower()].append(name)

        for comp_name in self.components:
            for target in sorted(self._import_targets.get(comp_name, ())):
                for other_comp in components_by_key.get(target, ()):
                    if other_comp != comp_name:
                        self.relationships.append((comp_name, other_comp, 'uses'))

    def _classify_layers(self):
        """Classify components into architectural layers."""
        for comp_name, comp_info in self.components.items():
            layer = comp_info.get('type', 'unknown')
            if layer != 'unknown':
                self.layers[layer].append(comp_name)
            else:
                self.layers['other'].append(comp_name)


class DiagramGenerator:
    """Base class for diagram generators."""

    def __init__(self, scan_result: Dict):
        self.components = scan_result['components']
        self.relationships = scan_result['relationships']
        self.layers = scan_result['layers']
        self.technologies = scan_result['technologies']
        self.external_deps = scan_result['external_deps']

    def generate(self, diagram_type: str) -> str:
        """Generate diagram based on type."""
        if diagram_type == 'component':
            return self._generate_component_diagram()
        elif diagram_type == 'layer':
            return self._generate_layer_diagram()
        elif diagram_type == 'deployment':
            return self._generate_deployment_diagram()
        else:
            return self._generate_component_diagram()

    def _generate_component_diagram(self) -> str:
        raise NotImplementedError

    def _generate_layer_diagram(self) -> str:
        raise NotImplementedError

    def _generate_deployment_diagram(self) -> str:
        raise NotImplementedError


class MermaidGenerator(DiagramGenerator):
    """Generate Mermaid diagrams."""

    def __init__(self, scan_result: Dict):
        super().__init__(scan_result)
        self._id_map: Dict[str, str] = {}
        self._used_ids: Set[str] = set()

    def _generate_component_diagram(self) -> str:
        lines = ['graph TD']

        # Add components
        for name, info in self.components.items():
            safe_name = self._safe_id(name)
            file_count = info.get('files', 0)
            lines.append(f'    {safe_name}["{self._safe_label(name)}<br/>{file_count} files"]')

        # Add relationships
        seen = set()
        for src, dst, rel_type in self.relationships:
            key = (src, dst)
            if key not in seen:
                seen.add(key)
                lines.append(f'    {self._safe_id(src)} --> {self._safe_id(dst)}')

        # Add external dependencies if any
        if self.external_deps:
            lines.append('')
            lines.append('    subgraph External')
            for dep in list(self.external_deps)[:5]:
                safe_dep = self._safe_id(dep)
                lines.append(f'        {safe_dep}(("{self._safe_label(dep)}"))')
            lines.append('    end')

        return '\n'.join(lines)

    def _generate_layer_diagram(self) -> str:
        lines = ['graph TB']

        layer_order = ['presentation', 'api', 'business', 'data', 'infrastructure', 'other']

        for layer in layer_order:
            components = self.layers.get(layer, [])
            if components:
                lines.append(f'    subgraph {layer.title()} Layer')
                for comp in components:
                    safe_comp = self._safe_id(comp)
                    lines.append(f'        {safe_comp}["{self._safe_label(comp)}"]')
                lines.append('    end')
                lines.append('')

        # Add layer relationships (top-down)
        prev_layer = None
        for layer in layer_order:
            if self.layers.get(layer):
                if prev_layer and self.layers.get(prev_layer):
                    first_prev = self._safe_id(self.layers[prev_layer][0])
                    first_curr = self._safe_id(self.layers[layer][0])
                    lines.append(f'    {first_prev} -.-> {first_curr}')
                prev_layer = layer

        return '\n'.join(lines)

    def _generate_deployment_diagram(self) -> str:
        lines = ['graph LR']

        # Client
        lines.append('    subgraph Client')
        lines.append('        browser["Browser/Mobile"]')
        lines.append('    end')
        lines.append('')

        # Determine if we have typical deployment components
        has_api = any('api' in t for t in self.technologies)
        has_docker = 'docker' in self.technologies
        has_k8s = 'kubernetes' in self.technologies

        # Application tier
        lines.append('    subgraph Application')
        if has_k8s:
            lines.append('        k8s["Kubernetes Cluster"]')
        elif has_docker:
            lines.append('        docker["Docker Container"]')
        else:
            lines.append('        app["Application Server"]')
        lines.append('    end')
        lines.append('')

        # Data tier
        lines.append('    subgraph Data')
        lines.append('        db[("Database")]')
        if self.external_deps:
            lines.append('        cache[("Cache")]')
        lines.append('    end')
        lines.append('')

        # Connections
        if has_k8s:
            lines.append('    browser --> k8s')
            lines.append('    k8s --> db')
        elif has_docker:
            lines.append('    browser --> docker')
            lines.append('    docker --> db')
        else:
            lines.append('    browser --> app')
            lines.append('    app --> db')

        return '\n'.join(lines)

    def _safe_id(self, name: str) -> str:
        """Convert name to a safe, collision-free, deterministic Mermaid ID.

        Names that differ only in non-alphanumeric characters (e.g.
        ``foo-bar`` vs ``foo_bar``) would collide under a simple
        ``[^a-zA-Z0-9] → _`` substitution.  A short deterministic hash
        suffix derived from the *original* name is used so that ID
        assignment never depends on traversal order.
        """
        if name in self._id_map:
            return self._id_map[name]
        base = re.sub(r'[^a-zA-Z0-9]', '_', name)
        if base == name and base not in self._used_ids:
            result = base
        else:
            suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            result = f'{base}_{suffix}'
            while result in self._used_ids:
                suffix = hashlib.md5(f'{name}{suffix}'.encode()).hexdigest()[:8]
                result = f'{base}_{suffix}'
        self._id_map[name] = result
        self._used_ids.add(result)
        return result

    def _safe_label(self, text: str) -> str:
        """Escape text for use inside Mermaid double-quoted labels."""
        return text.replace('"', '&quot;')


class PlantUMLGenerator(DiagramGenerator):
    """Generate PlantUML diagrams."""

    def __init__(self, scan_result: Dict):
        super().__init__(scan_result)
        self._id_map: Dict[str, str] = {}
        self._used_ids: Set[str] = set()

    def _generate_component_diagram(self) -> str:
        lines = ['@startuml', 'skinparam componentStyle rectangle', '']

        # Add components
        for name, info in self.components.items():
            file_count = info.get('files', 0)
            lines.append(f'component "{name}\\n({file_count} files)" as {self._safe_id(name)}')

        lines.append('')

        # Add relationships
        seen = set()
        for src, dst, rel_type in self.relationships:
            key = (src, dst)
            if key not in seen:
                seen.add(key)
                lines.append(f'{self._safe_id(src)} --> {self._safe_id(dst)}')

        # External dependencies
        if self.external_deps:
            lines.append('')
            lines.append('package "External Dependencies" {')
            for dep in list(self.external_deps)[:5]:
                lines.append(f'  [{dep}]')
            lines.append('}')

        lines.append('')
        lines.append('@enduml')
        return '\n'.join(lines)

    def _generate_layer_diagram(self) -> str:
        lines = ['@startuml', 'skinparam packageStyle rectangle', '']

        layer_order = ['presentation', 'api', 'business', 'data', 'infrastructure', 'other']

        for layer in layer_order:
            components = self.layers.get(layer, [])
            if components:
                lines.append(f'package "{layer.title()} Layer" {{')
                for comp in components:
                    lines.append(f'  [{comp}]')
                lines.append('}')
                lines.append('')

        lines.append('@enduml')
        return '\n'.join(lines)

    def _generate_deployment_diagram(self) -> str:
        lines = ['@startuml', '']

        lines.append('node "Client" {')
        lines.append('  [Browser/Mobile] as browser')
        lines.append('}')
        lines.append('')

        has_docker = 'docker' in self.technologies
        has_k8s = 'kubernetes' in self.technologies

        lines.append('node "Application Server" {')
        if has_k8s:
            lines.append('  [Kubernetes Cluster] as app')
        elif has_docker:
            lines.append('  [Docker Container] as app')
        else:
            lines.append('  [Application] as app')
        lines.append('}')
        lines.append('')

        lines.append('database "Data Store" {')
        lines.append('  [Database] as db')
        lines.append('}')
        lines.append('')

        lines.append('browser --> app')
        lines.append('app --> db')
        lines.append('')
        lines.append('@enduml')
        return '\n'.join(lines)

    def _safe_id(self, name: str) -> str:
        """Convert name to a safe, collision-free, deterministic PlantUML ID.

        Uses a deterministic hash suffix derived from the original name
        so that ID assignment never depends on traversal order.
        """
        if name in self._id_map:
            return self._id_map[name]
        base = re.sub(r'[^a-zA-Z0-9]', '_', name)
        if base == name and base not in self._used_ids:
            result = base
        else:
            suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            result = f'{base}_{suffix}'
            while result in self._used_ids:
                suffix = hashlib.md5(f'{name}{suffix}'.encode()).hexdigest()[:8]
                result = f'{base}_{suffix}'
        self._id_map[name] = result
        self._used_ids.add(result)
        return result


class ASCIIGenerator(DiagramGenerator):
    """Generate ASCII diagrams."""

    def _generate_component_diagram(self) -> str:
        lines = []
        lines.append('=' * 60)
        lines.append('COMPONENT DIAGRAM')
        lines.append('=' * 60)
        lines.append('')

        # Components
        lines.append('Components:')
        lines.append('-' * 40)
        for name, info in self.components.items():
            file_count = info.get('files', 0)
            comp_type = info.get('type', 'unknown')
            lines.append(f'  [{name}]')
            lines.append(f'      Files: {file_count}')
            lines.append(f'      Type: {comp_type}')
            lines.append('')

        # Relationships
        if self.relationships:
            lines.append('Relationships:')
            lines.append('-' * 40)
            seen = set()
            for src, dst, rel_type in self.relationships:
                key = (src, dst)
                if key not in seen:
                    seen.add(key)
                    lines.append(f'  {src} --> {dst}')
            lines.append('')

        # External dependencies
        if self.external_deps:
            lines.append('External Dependencies:')
            lines.append('-' * 40)
            for dep in list(self.external_deps)[:10]:
                lines.append(f'  - {dep}')

        lines.append('')
        lines.append('=' * 60)
        return '\n'.join(lines)

    def _generate_layer_diagram(self) -> str:
        lines = []
        lines.append('=' * 60)
        lines.append('LAYERED ARCHITECTURE')
        lines.append('=' * 60)
        lines.append('')

        layer_order = ['presentation', 'api', 'business', 'data', 'infrastructure', 'other']

        for layer in layer_order:
            components = self.layers.get(layer, [])
            if components:
                lines.append(f'+{"-" * 56}+')
                lines.append(f'| {layer.upper():^54} |')
                lines.append(f'+{"-" * 56}+')
                for comp in components:
                    lines.append(f'|   [{comp:^48}]   |')
                lines.append(f'+{"-" * 56}+')
                lines.append('           |')
                lines.append('           v')

        # Remove last arrow
        if lines[-2:] == ['           |', '           v']:
            lines = lines[:-2]

        lines.append('')
        lines.append('=' * 60)
        return '\n'.join(lines)

    def _generate_deployment_diagram(self) -> str:
        lines = []
        lines.append('=' * 60)
        lines.append('DEPLOYMENT DIAGRAM')
        lines.append('=' * 60)
        lines.append('')

        has_docker = 'docker' in self.technologies
        has_k8s = 'kubernetes' in self.technologies

        # Client tier
        lines.append('+----------------------+')
        lines.append('|       CLIENT         |')
        lines.append('|  [Browser/Mobile]    |')
        lines.append('+----------+-----------+')
        lines.append('           |')
        lines.append('           v')

        # Application tier
        lines.append('+----------------------+')
        lines.append('|     APPLICATION      |')
        if has_k8s:
            lines.append('| [Kubernetes Cluster] |')
        elif has_docker:
            lines.append('| [Docker Container]   |')
        else:
            lines.append('| [App Server]         |')
        lines.append('+----------+-----------+')
        lines.append('           |')
        lines.append('           v')

        # Data tier
        lines.append('+----------------------+')
        lines.append('|        DATA          |')
        lines.append('|     [(Database)]     |')
        lines.append('+----------------------+')

        lines.append('')

        # Technologies detected
        if self.technologies:
            lines.append('Technologies detected:')
            lines.append('-' * 40)
            for tech in sorted(self.technologies):
                lines.append(f'  - {tech}')

        lines.append('')
        lines.append('=' * 60)
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate architecture diagrams from project structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s ./my-project --format mermaid
  %(prog)s ./my-project --format plantuml --type layer
  %(prog)s ./my-project --format ascii -o architecture.txt

Diagram types:
  component   - Shows modules and their relationships (default)
  layer       - Shows architectural layers
  deployment  - Shows deployment topology

Output formats:
  mermaid     - Mermaid.js format (default)
  plantuml    - PlantUML format
  ascii       - ASCII art format
        '''
    )

    parser.add_argument(
        'project_path',
        help='Path to the project directory'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['mermaid', 'plantuml', 'ascii'],
        default='mermaid',
        help='Output format (default: mermaid)'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['component', 'layer', 'deployment'],
        default='component',
        help='Diagram type (default: component)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (prints to stdout if not specified)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output raw scan results as JSON'
    )

    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}", file=sys.stderr)
        sys.exit(1)

    if not project_path.is_dir():
        print(f"Error: Project path is not a directory: {project_path}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Scanning project: {project_path}")

    # Scan project
    scanner = ProjectScanner(project_path)
    scan_result = scanner.scan()

    if args.verbose:
        print(f"Found {len(scan_result['components'])} components")
        print(f"Found {len(scan_result['relationships'])} relationships")
        print(f"Technologies: {', '.join(scan_result['technologies']) or 'none detected'}")

    # Output raw JSON if requested
    if args.json:
        output = json.dumps(scan_result, indent=2)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Results written to {args.output}")
        else:
            print(output)
        return

    # Generate diagram
    generators = {
        'mermaid': MermaidGenerator,
        'plantuml': PlantUMLGenerator,
        'ascii': ASCIIGenerator,
    }

    generator = generators[args.format](scan_result)
    diagram = generator.generate(args.type)

    # Output
    if args.output:
        Path(args.output).write_text(diagram)
        print(f"Diagram written to {args.output}")
    else:
        print(diagram)


if __name__ == '__main__':
    main()
