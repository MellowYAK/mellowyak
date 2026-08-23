from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from mellowyak_engine.scanning.policy import MAX_STORED_PARSER_ITEMS


@dataclass(frozen=True)
class ParsedReference:
    value: str
    relation: str


@dataclass(frozen=True)
class ParsedDeclaration:
    name: str
    node_type: str = "SYMBOL"


@dataclass(frozen=True)
class ParseResult:
    adapter: str
    provenance: str
    references: tuple[ParsedReference, ...]
    declarations: tuple[ParsedDeclaration, ...]
    warnings: tuple[str, ...] = ()


class ParserAdapter:
    languages: frozenset[str] = frozenset()

    def parse(self, text: str) -> ParseResult:
        raise NotImplementedError


class PythonAstAdapter(ParserAdapter):
    languages = frozenset({"Python"})

    def parse(self, text: str) -> ParseResult:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError) as error:
            return ParseResult("python-ast-v1", "STATIC_PARSED", (), (), (type(error).__name__,))
        references: list[ParsedReference] = []
        declarations: list[ParsedDeclaration] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                references.extend(ParsedReference(item.name, "IMPORTS") for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                prefix = "." * node.level
                references.append(ParsedReference(prefix + (node.module or ""), "IMPORTS"))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                declarations.append(ParsedDeclaration(node.name))
        return ParseResult(
            "python-ast-v1",
            "STATIC_PARSED",
            tuple(references[:MAX_STORED_PARSER_ITEMS]),
            tuple(declarations[:MAX_STORED_PARSER_ITEMS]),
        )


class EcmaImportAdapter(ParserAdapter):
    languages = frozenset({"JavaScript", "JavaScript JSX", "TypeScript", "TypeScript TSX"})
    _imports = re.compile(
        r"(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|require\s*\()"
        r"[\"']([^\"']+)[\"']"
    )
    _declarations = re.compile(
        r"\b(?:export\s+)?(?:async\s+)?(?:function|class|interface|type)\s+([A-Za-z_$][\w$]*)"
    )

    def parse(self, text: str) -> ParseResult:
        references = tuple(
            ParsedReference(value, "IMPORTS")
            for value in self._imports.findall(text)[:MAX_STORED_PARSER_ITEMS]
        )
        declarations = tuple(
            ParsedDeclaration(value)
            for value in self._declarations.findall(text)[:MAX_STORED_PARSER_ITEMS]
        )
        return ParseResult("ecma-import-scanner-v1", "STATIC_HEURISTIC", references, declarations)


class PhpIncludeAdapter(ParserAdapter):
    languages = frozenset({"PHP"})
    _includes = re.compile(
        r"\b(?:include|include_once|require|require_once)\s*(?:\(\s*)?[\"']([^\"']+)[\"']",
        re.IGNORECASE,
    )
    _declarations = re.compile(r"\b(?:function|class|interface|trait)\s+([A-Za-z_][\w]*)")

    def parse(self, text: str) -> ParseResult:
        references = tuple(
            ParsedReference(value, "INCLUDES")
            for value in self._includes.findall(text)[:MAX_STORED_PARSER_ITEMS]
        )
        declarations = tuple(
            ParsedDeclaration(value)
            for value in self._declarations.findall(text)[:MAX_STORED_PARSER_ITEMS]
        )
        return ParseResult("php-include-scanner-v1", "STATIC_HEURISTIC", references, declarations)


ADAPTERS: tuple[ParserAdapter, ...] = (
    PythonAstAdapter(),
    EcmaImportAdapter(),
    PhpIncludeAdapter(),
)


def adapter_for(language: str) -> ParserAdapter | None:
    return next((adapter for adapter in ADAPTERS if language in adapter.languages), None)
