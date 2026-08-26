import json

DATA = [
  {
    "repository": "psf/black",
    "entry_point": { "answer": "src/black/__init__.py", "evidence": "pyproject.toml" },
    "run_command": "black {source_file_or_directory}",
    "framework": "Click",
    "architecture": "CLI / Script"
  },
  {
    "repository": "pallets/flask",
    "entry_point": { "answer": "src/flask/__init__.py", "evidence": "src/flask/__init__.py" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "tiangolo/fastapi",
    "entry_point": { "answer": "fastapi/__init__.py", "evidence": "fastapi/__init__.py" },
    "run_command": None,
    "framework": "Starlette",
    "architecture": "Library"
  },
  {
    "repository": "Textualize/rich",
    "entry_point": { "answer": "rich/__init__.py", "evidence": "rich/__init__.py" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "expressjs/express",
    "entry_point": { "answer": "index.js", "evidence": "package.json" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "facebook/react",
    "entry_point": { "answer": None, "evidence": None },
    "run_command": None,
    "framework": None,
    "architecture": "Monorepo"
  },
  {
    "repository": "nestjs/nest",
    "entry_point": { "answer": None, "evidence": None },
    "run_command": None,
    "framework": None,
    "architecture": "Monorepo"
  },
  {
    "repository": "gin-gonic/gin",
    "entry_point": { "answer": "gin.go", "evidence": "gin.go" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "spf13/cobra",
    "entry_point": { "answer": "cobra.go", "evidence": "cobra.go" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "gohugoio/hugo",
    "entry_point": { "answer": "main.go", "evidence": "main.go" },
    "run_command": "go run main.go",
    "framework": None,
    "architecture": "CLI / Script"
  },
  {
    "repository": "spring-projects/spring-petclinic",
    "entry_point": { "answer": "src/main/java/org/springframework/samples/petclinic/PetClinicApplication.java", "evidence": "pom.xml" },
    "run_command": "./mvnw spring-boot:run",
    "framework": "Spring Boot",
    "architecture": "Backend / API"
  },
  {
    "repository": "google/guava",
    "entry_point": { "answer": None, "evidence": None },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "nlohmann/json",
    "entry_point": { "answer": "include/nlohmann/json.hpp", "evidence": "CMakeLists.txt" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "redis/redis",
    "entry_point": { "answer": "src/server.c", "evidence": "Makefile" },
    "run_command": "make && src/redis-server",
    "framework": None,
    "architecture": "Backend / API"
  },
  {
    "repository": "rust-lang/cargo",
    "entry_point": { "answer": "src/bin/cargo/main.rs", "evidence": "Cargo.toml" },
    "run_command": "cargo run",
    "framework": None,
    "architecture": "CLI / Script"
  },
  {
    "repository": "tokio-rs/tokio",
    "entry_point": { "answer": "tokio/src/lib.rs", "evidence": "tokio/Cargo.toml" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "babel/babel",
    "entry_point": { "answer": None, "evidence": None },
    "run_command": None,
    "framework": None,
    "architecture": "Monorepo"
  },
  {
    "repository": "angular/angular",
    "entry_point": { "answer": None, "evidence": None },
    "run_command": None,
    "framework": None,
    "architecture": "Monorepo"
  },
  {
    "repository": "chalk/chalk",
    "entry_point": { "answer": "source/index.js", "evidence": "package.json" },
    "run_command": None,
    "framework": None,
    "architecture": "Library"
  },
  {
    "repository": "pypa/pip",
    "entry_point": { "answer": "src/pip/__main__.py", "evidence": "pyproject.toml" },
    "run_command": "python -m pip",
    "framework": None,
    "architecture": "CLI / Script"
  },
  {
    "repository": "gothinkster/node-express-realworld-example-app",
    "entry_point": { "answer": "app.js", "evidence": "package.json" },
    "run_command": "npm start",
    "framework": "Express",
    "architecture": "Backend / API"
  },
  {
    "repository": "gothinkster/golang-gin-realworld-example-app",
    "entry_point": { "answer": "main.go", "evidence": "main.go" },
    "run_command": "go run main.go",
    "framework": "Gin",
    "architecture": "Backend / API"
  }
]

with open("research/ground_truth.json", "w") as f:
    json.dump(DATA, f, indent=2)
print("Updated research/ground_truth.json")
