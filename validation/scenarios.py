from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass
class Scenario:
    name: str
    files: Dict[str, str]
    expected: Dict[str, Any]

def get_scenarios() -> List[Scenario]:
    return [
        Scenario(
            name="python_cli",
            files={
                "main.py": "import sys\nimport utils\n\nif __name__ == '__main__':\n    pass",
                "utils.py": "def helper(): pass",
                "requirements.txt": "click==8.1.3",
                "tests/test_main.py": "def test_main(): pass"
            },
            expected={
                "languages": {"required": ["Python"]},
                "entry_points": {"required": ["main.py"]},
                "important_files": {"required": ["requirements.txt"]},
                "architecture_patterns": {"required": ["Flat / Script-based"]}
            }
        ),
        Scenario(
            name="fastapi_app",
            files={
                "app/main.py": "from fastapi import FastAPI\nfrom app.routes import api\n\napp = FastAPI()",
                "app/routes/api.py": "def router(): pass",
                "app/services/user.py": "def get_user(): pass",
                "app/models/db.py": "class User: pass",
                "config.py": "DATABASE_URL=''",
                "requirements.txt": "fastapi==0.95.0\nuvicorn==0.21.1",
                "README.md": "# Setup\n\n```bash\npython -m venv venv\npip install -r requirements.txt\n```\n# Usage\n```bash\nuvicorn app.main:app --reload\n```"
            },
            expected={
                "languages": {"required": ["Python"]},
                "frameworks": {"required": ["FastAPI"]},
                "entry_points": {"required": ["app/main.py"]},
                "important_files": {"required": ["requirements.txt"]},
                "architecture_patterns": {"required": ["Backend/API application", "Layered"]},
                "run_instructions": {"required": ["pip install -r requirements.txt", "uvicorn app.main:app --reload"]}
            }
        ),
        Scenario(
            name="node_app",
            files={
                "package.json": '{"name": "test", "main": "src/index.js", "scripts": {"start": "node src/index.js", "test": "jest"}}',
                "package-lock.json": "{}",
                "src/index.js": "const express = require('express');\nconst app = express();",
                "src/services/auth.js": "module.exports = {};",
                "src/routes/api.js": "module.exports = {};",
                "test/app.test.js": "test('works', () => {});"
            },
            expected={
                "languages": {"required": ["JavaScript"]},
                "package_managers": {"required": ["npm"]},
                "manifests": {"required": ["package.json", "package-lock.json"]},
                "entry_points": {"required": ["src/index.js"]},
                "architecture_patterns": {"required": ["Backend/API application"]},
                "run_instructions": {"required": ["npm run start", "npm run test", "npm install"]}
            }
        ),
        Scenario(
            name="react_app",
            files={
                "package.json": '{"dependencies": {"react": "^18.2.0"}}',
                "yarn.lock": "...",
                "src/main.tsx": "import React from 'react';\nimport { createRoot } from 'react-dom/client';",
                "src/App.tsx": "export default function App() {}",
                "src/components/Button.tsx": "export function Button() {}",
                "src/pages/Home.tsx": "export default function Home() {}",
                "src/hooks/useData.ts": "export function useData() {}"
            },
            expected={
                "languages": {"required": ["TypeScript"]},
                "frameworks": {"required": ["React"]},
                "package_managers": {"required": ["yarn"]},
                "manifests": {"required": ["package.json"]},
                "architecture_patterns": {"required": ["Frontend application"]}
            }
        ),
        Scenario(
            name="go_app",
            files={
                "go.mod": "module github.com/foo/bar\n\ngo 1.20",
                "cmd/server/main.go": "package main\n\nimport \"fmt\"\n\nfunc main() {}",
                "internal/auth/auth.go": "package auth",
                "pkg/utils/utils.go": "package utils"
            },
            expected={
                "languages": {"required": ["Go"]},
                "manifests": {"required": ["go.mod"]},
                "entry_points": {"required": ["cmd/server/main.go"]}
            }
        ),
        Scenario(
            name="monorepo",
            files={
                "package.json": '{"workspaces": ["apps/*", "packages/*"]}',
                "apps/web/package.json": '{"name": "web"}',
                "apps/api/package.json": '{"name": "api"}',
                "packages/ui/package.json": '{"name": "ui"}'
            },
            expected={
                "manifests": {"required": ["package.json", "apps/web/package.json", "apps/api/package.json", "packages/ui/package.json"]},
                "architecture_patterns": {"required": ["Monorepo"]}
            }
        ),
        Scenario(
            name="large_repo",
            files={
                "main.py": "if __name__ == '__main__': pass",
                ".git/config": "...",
                "node_modules/express/index.js": "...",
                ".venv/bin/python": "..."
            } | {f"src/file_{i}.py": "pass" for i in range(100)} 
              | {f"node_modules/lib_{i}/index.js": "..." for i in range(200)},
            expected={
                "languages": {"required": ["Python"]},
                "entry_points": {"required": ["main.py"]}
            }
        )
    ]
