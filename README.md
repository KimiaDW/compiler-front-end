# Compiler Front-End

A robust, educational compiler front-end implemented in Python. It performs three complete compilation phases—**Lexical Analysis**, **Syntax Analysis**, and **Semantic Analysis**—on a custom C-like programming language, complete with error recovery and detailed diagnostic reporting.

## Features

- **Lexical Analyzer (Lexer):** 
  - Tokenizes source code into keywords (`if`, `else`, `while`, `for`, `int`, `float`, `return`, `void`, `string`), operators, delimiters, numbers, identifiers, and strings.
  - Tracks line and column numbers for precise error reporting.
- **Syntax Analyzer (Parser):**
  - Recursive-descent parser building an Abstract Syntax Tree (AST).
  - Built-in error recovery (`synchronize` mechanism) to catch multiple syntax errors per run.
  - Pretty-prints the AST in a structured ASCII tree format.
- **Semantic Analyzer & Symbol Table:**
  - Scoped symbol table handling variable/function declarations, scope entry/exit, and type/initialization checks.
  - Generates an annotated semantic tree and exports results in JSON format.
- **Diagnostic Reporting:**
  - Aggregates lexical, syntactic, and semantic errors and warnings.
  - Displays offending source lines with visual pointers (`^`) pointing to the exact error column.

## Requirements

- **Python 3.x**
- Uses Python standard libraries only (`enum`, `typing`, `dataclasses`, `json`). **No external third-party packages required.**

## Usage

Run the script from your terminal:
```bash
python Compiler_Front_End.py
