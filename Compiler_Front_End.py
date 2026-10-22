from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import json


class TokenType(Enum):
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    OPERATOR = "OPERATOR"
    DELIMITER = "DELIMITER"
    STRING = "STRING"
    COMMENT = "COMMENT"
    EOF = "EOF"             #End Of File


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int


@dataclass
class CompileMessage:
    phase: str   
    message: str               
    line: Optional[int] = None
    column: Optional[int] = None

    def __str__(self) -> str:
        loc = ""
        if self.line is not None:
            loc = f" (line {self.line})" if self.column is None else f" (line {self.line}, col {self.column})"
        return f"[{self.phase}] {self.message}{loc}"


class Lexer:

    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []
        self.keywords = {'if', 'else', 'while', 'for', 'int', 'float', 'return', 'void', 'string'}
        self.operators = {'+', '-', '*', '/', '=', '==', '!=', '<', '>', '<=', '>=', '&&', '||', '!'}
        self.delimiters = {';', ',', '(', ')', '{', '}', '[', ']'}
    
    def current_char(self) -> Optional[str]:
        if self.position >= len(self.source):
            return None
        return self.source[self.position]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        pos = self.position + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self):
        if self.position < len(self.source):
            if self.source[self.position] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.position += 1
    
    def skip_whitespace(self):
        while self.current_char() and self.current_char() in ' \t\n\r':
            self.advance()
    
    def read_number(self) -> Token:
        start_line = self.line
        start_column = self.column
        num_str = ''
        dot_seen = False
        
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                if dot_seen:
                    break
                dot_seen = True
            num_str += self.current_char()
            self.advance()
        
        return Token(TokenType.NUMBER, num_str, start_line, start_column)
    
    def read_identifier(self) -> Token:
        start_line = self.line
        start_column = self.column
        id_str = ''
        
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            id_str += self.current_char()
            self.advance()
        
        token_type = TokenType.KEYWORD if id_str in self.keywords else TokenType.IDENTIFIER
        return Token(token_type, id_str, start_line, start_column)
    
    def read_string(self) -> Token:
        start_line = self.line
        start_column = self.column
        self.advance()
        str_value = ''
        
        while self.current_char() and self.current_char() != '"':
            str_value += self.current_char()
            self.advance()
        
        if self.current_char() == '"':
            self.advance()
        else:
            self.errors.append(CompileMessage(
                phase="Lexical",
                message="Unterminated string literal",
                line=start_line,
                column=start_column
            ))
        
        return Token(TokenType.STRING, str_value, start_line, start_column)
    
    def read_line_comment(self) -> Token:
        start_line = self.line
        start_column = self.column

        self.advance() 
        self.advance() 

        comment_str = ''
        while self.current_char() and self.current_char() != '\n':
            comment_str += self.current_char()
            self.advance()

        return Token(TokenType.COMMENT, comment_str.strip(), start_line, start_column)

    def read_block_comment(self) -> Token:
        start_line = self.line
        start_column = self.column

        self.advance()
        self.advance()

        comment_str = ''
        closed = False
        while self.current_char():
            if self.current_char() == '*' and self.peek_char() == '/':
                self.advance()
                self.advance()
                closed = True
                break
            comment_str += self.current_char()
            self.advance()

        if not closed:
            self.errors.append(CompileMessage(
                phase="Lexical",
                message="Unterminated block comment",
                line=start_line,
                column=start_column
            ))

        return Token(TokenType.COMMENT, comment_str.strip(), start_line, start_column)

    def read_operator(self) -> Token:
        start_line = self.line
        start_column = self.column
        op = self.current_char()
        self.advance()
        
        if self.current_char() and op + self.current_char() in self.operators:
            op += self.current_char()
            self.advance()
        
        return Token(TokenType.OPERATOR, op, start_line, start_column)
    
    def tokenize(self) -> List[Token]:
        while self.current_char():
            self.skip_whitespace()
            
            if not self.current_char():
                break
            
            char = self.current_char()
            
            if char == '/' and self.peek_char() == '/':
                self.tokens.append(self.read_line_comment())
            elif char == '/' and self.peek_char() == '*':
                self.tokens.append(self.read_block_comment())
            elif char.isdigit():
                self.tokens.append(self.read_number())
            elif char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
            elif char == '"':
                self.tokens.append(self.read_string())
            elif char in self.delimiters:
                self.tokens.append(Token(TokenType.DELIMITER, char, self.line, self.column))
                self.advance()
            elif char in {'+', '-', '*', '/', '=', '!', '<', '>', '&', '|'}:
                self.tokens.append(self.read_operator())
            else:
                self.errors.append(CompileMessage(
                    phase="Lexical",
                    message=f"Unexpected character '{char}'",
                    line=self.line,
                    column=self.column
                ))
                self.advance()
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


@dataclass
class ASTNode:
    node_type: str
    value: Any = None
    children: List['ASTNode'] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


class ParseError(Exception):
    pass


STATEMENT_START_KEYWORDS = {'if', 'while', 'for', 'return', 'int', 'float', 'string', 'void'}


class Parser:

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.errors = []
    
    def current_token(self) -> Token:
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return self.tokens[-1]
    
    def peek_token(self, offset: int = 1) -> Token:
        pos = self.position + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]
    
    def advance(self):
        if self.position < len(self.tokens) - 1:
            self.position += 1
    
    def expect(self, token_type: TokenType, value: Optional[str] = None) -> bool:
        token = self.current_token()
        if token.type == token_type and (value is None or token.value == value):
            self.advance()
            return True
        expected = f"{token_type.value} '{value}'" if value else token_type.value
        self.errors.append(CompileMessage(
            phase="Syntax",
            message=f"Expected {expected} but got '{token.value}'",
            line=token.line,
            column=token.column
        ))
        return False
    
    def synchronize(self):
        while self.current_token().type != TokenType.EOF:
            token = self.current_token()
            
            if token.type == TokenType.KEYWORD and token.value in STATEMENT_START_KEYWORDS:
                return
            if token.value == '{':
                return
            if token.value in (';', '}'):
                self.advance()
                return
            
            self.advance()
    
    def parse(self) -> ASTNode:
        root = ASTNode("Program")
        
        while self.current_token().type != TokenType.EOF:
            start_position = self.position
            try:
                stmt = self.parse_statement()
                if stmt:
                    root.children.append(stmt)
            except ParseError:
                self.synchronize()
            
            if self.position == start_position:
                self.advance()
        
        return root
    
    def parse_statement(self) -> Optional[ASTNode]:
        token = self.current_token()
        
        if token.type == TokenType.KEYWORD:
            if token.value in {'int', 'float', 'string', 'void'}:
                return self.parse_declaration()
            elif token.value == 'if':
                return self.parse_if_statement()
            elif token.value == 'while':
                return self.parse_while_statement()
            elif token.value == 'for':
                return self.parse_for_statement()
            elif token.value == 'return':
                return self.parse_return_statement()
        
        return self.parse_expression_statement()
    
    def parse_declaration(self) -> ASTNode:
        type_token = self.current_token()
        self.advance()
        
        name_token = self.current_token()
        node = ASTNode("Declaration", attributes={
            'type': type_token.value, 'name': name_token.value, 'line': type_token.line
        })
        
        if name_token.type == TokenType.IDENTIFIER:
            self.advance()
            
            if self.current_token().value == '(':
                return self.parse_function_declaration(type_token.value, name_token.value, type_token.line)
            
            if self.current_token().value == '=':
                self.advance()
                node.children.append(self.parse_expression())
            
            self.expect(TokenType.DELIMITER, ';')
        else:
            self.errors.append(CompileMessage(
                phase="Syntax",
                message=f"Expected identifier after type '{type_token.value}' but got '{name_token.value}'",
                line=name_token.line,
                column=name_token.column
            ))
            self.advance()
        
        return node
    
    def parse_function_declaration(self, return_type: str, name: str, line: int) -> ASTNode:
        node = ASTNode("FunctionDeclaration", attributes={'type': return_type, 'name': name, 'line': line})
        
        self.expect(TokenType.DELIMITER, '(')
        
        params = []
        while self.current_token().value != ')' and self.current_token().type != TokenType.EOF:
            if self.current_token().type == TokenType.KEYWORD:
                param_type = self.current_token().value
                self.advance()
                param_token = self.current_token()
                param_name = param_token.value
                self.advance()
                params.append({'type': param_type, 'name': param_name, 'line': param_token.line})
                
                if self.current_token().value == ',':
                    self.advance()
            else:
                token = self.current_token()
                self.errors.append(CompileMessage(
                    phase="Syntax",
                    message=f"Expected parameter type but got '{token.value}'",
                    line=token.line,
                    column=token.column
                ))
                self.advance()
        
        node.attributes['params'] = params
        self.expect(TokenType.DELIMITER, ')')
        
        if self.current_token().value == '{':
            node.children.append(self.parse_block())
        
        return node
    
    def parse_block(self) -> ASTNode:
        node = ASTNode("Block")
        self.expect(TokenType.DELIMITER, '{')
        
        while self.current_token().value != '}' and self.current_token().type != TokenType.EOF:
            start_position = self.position
            try:
                stmt = self.parse_statement()
                if stmt:
                    node.children.append(stmt)
            except ParseError:
                self.synchronize()
            
            if self.position == start_position:
                self.advance()
        
        self.expect(TokenType.DELIMITER, '}')
        return node
    
    def parse_if_statement(self) -> ASTNode:
        node = ASTNode("IfStatement")
        self.advance()
        
        self.expect(TokenType.DELIMITER, '(')
        node.children.append(self.parse_expression())
        self.expect(TokenType.DELIMITER, ')')
        
        node.children.append(self.parse_block())
        
        if self.current_token().value == 'else':
            self.advance()
            node.children.append(self.parse_block())
        
        return node
    
    def parse_while_statement(self) -> ASTNode:
        node = ASTNode("WhileStatement")
        self.advance()
        
        self.expect(TokenType.DELIMITER, '(')
        node.children.append(self.parse_expression())
        self.expect(TokenType.DELIMITER, ')')
        
        node.children.append(self.parse_block())
        
        return node
    
    def parse_for_statement(self) -> ASTNode:
        node = ASTNode("ForStatement")
        self.advance()
        
        self.expect(TokenType.DELIMITER, '(')
        node.children.append(self.parse_statement())
        node.children.append(self.parse_expression())
        self.expect(TokenType.DELIMITER, ';')
        node.children.append(self.parse_expression())
        self.expect(TokenType.DELIMITER, ')')
        
        node.children.append(self.parse_block())
        
        return node
    
    def parse_return_statement(self) -> ASTNode:
        """Parses a 'return [expression];' statement."""
        return_token = self.current_token()
        node = ASTNode("ReturnStatement", attributes={'line': return_token.line})
        self.advance()
        
        if self.current_token().value != ';':
            node.children.append(self.parse_expression())
        
        self.expect(TokenType.DELIMITER, ';')
        return node
    
    def parse_expression_statement(self) -> ASTNode:
        node = self.parse_expression()
        self.expect(TokenType.DELIMITER, ';')
        return node
    
    def parse_expression(self) -> ASTNode:
        return self.parse_assignment()
    
    def parse_assignment(self) -> ASTNode:
        node = self.parse_logical_or()
        
        if self.current_token().value == '=':
            op_token = self.current_token()
            self.advance()
            right = self.parse_assignment()
            return ASTNode("Assignment", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_logical_or(self) -> ASTNode:
        node = self.parse_logical_and()
        
        while self.current_token().value == '||':
            op_token = self.current_token()
            self.advance()
            right = self.parse_logical_and()
            node = ASTNode("BinaryOp", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_logical_and(self) -> ASTNode:
        node = self.parse_equality()
        
        while self.current_token().value == '&&':
            op_token = self.current_token()
            self.advance()
            right = self.parse_equality()
            node = ASTNode("BinaryOp", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_equality(self) -> ASTNode:
        node = self.parse_relational()
        
        while self.current_token().value in {'==', '!='}:
            op_token = self.current_token()
            self.advance()
            right = self.parse_relational()
            node = ASTNode("BinaryOp", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_relational(self) -> ASTNode:
        node = self.parse_additive()
        
        while self.current_token().value in {'<', '>', '<=', '>='}:
            op_token = self.current_token()
            self.advance()
            right = self.parse_additive()
            node = ASTNode("BinaryOp", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_additive(self) -> ASTNode:
        node = self.parse_multiplicative()
        
        while self.current_token().value in {'+', '-'}:
            op_token = self.current_token()
            self.advance()
            right = self.parse_multiplicative()
            node = ASTNode("BinaryOp", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_multiplicative(self) -> ASTNode:
        node = self.parse_unary()
        
        while self.current_token().value in {'*', '/'}:
            op_token = self.current_token()
            self.advance()
            right = self.parse_unary()
            node = ASTNode("BinaryOp", op_token.value, [node, right], attributes={'line': op_token.line})
        
        return node
    
    def parse_unary(self) -> ASTNode:
        if self.current_token().value in {'-', '!'}:
            op_token = self.current_token()
            self.advance()
            return ASTNode("UnaryOp", op_token.value, [self.parse_unary()], attributes={'line': op_token.line})
        
        return self.parse_primary()
    
    def parse_primary(self) -> ASTNode:
        token = self.current_token()
        
        if token.type == TokenType.NUMBER:
            self.advance()
            return ASTNode("Literal", token.value, attributes={'type': 'number', 'line': token.line})
        
        elif token.type == TokenType.STRING:
            self.advance()
            return ASTNode("Literal", token.value, attributes={'type': 'string', 'line': token.line})
        
        elif token.type == TokenType.IDENTIFIER:
            name = token.value
            self.advance()
            
            if self.current_token().value == '(':
                return self.parse_function_call(name, token.line)
            
            return ASTNode("Identifier", name, attributes={'line': token.line})
        
        elif token.value == '(':
            self.advance()
            node = self.parse_expression()
            self.expect(TokenType.DELIMITER, ')')
            return node
        
        self.errors.append(CompileMessage(
            phase="Syntax",
            message=f"Unexpected token '{token.value}'",
            line=token.line,
            column=token.column
        ))
        if token.type != TokenType.EOF:
            self.advance()
        raise ParseError(f"Unexpected token '{token.value}' at line {token.line}")
    
    def parse_function_call(self, name: str, line: int) -> ASTNode:
        node = ASTNode("FunctionCall", name, attributes={'line': line})
        self.expect(TokenType.DELIMITER, '(')
        
        while self.current_token().value != ')' and self.current_token().type != TokenType.EOF:
            node.children.append(self.parse_expression())
            
            if self.current_token().value == ',':
                self.advance()
        
        self.expect(TokenType.DELIMITER, ')')
        return node


class Symbol:

    def __init__(self, name: str, symbol_type: str, scope: int, value_type: Optional[str] = None,
                 params: Optional[List[Dict[str, str]]] = None):
        self.name = name
        self.symbol_type = symbol_type
        self.scope = scope
        self.value_type = value_type
        self.is_initialized = False
        self.params = params  


class SymbolTable:

    def __init__(self):
        self.scopes = [{}]
    
    @property
    def current_scope(self) -> int:
        return len(self.scopes) - 1
    
    def enter_scope(self):
        self.scopes.append({})
    
    def exit_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def declare(self, name: str, symbol_type: str, value_type: Optional[str] = None,
                params: Optional[List[Dict[str, str]]] = None) -> bool:
        if name in self.scopes[self.current_scope]:
            return False
        
        self.scopes[self.current_scope][name] = Symbol(name, symbol_type, self.current_scope, value_type, params)
        return True
    
    def lookup(self, name: str) -> Optional[Symbol]:
        for i in range(self.current_scope, -1, -1):
            if name in self.scopes[i]:
                return self.scopes[i][name]
        return None
    
    def update_initialization(self, name: str):
        symbol = self.lookup(name)
        if symbol:
            symbol.is_initialized = True


class SemanticAnalyzer:

    def __init__(self, ast: ASTNode):
        self.ast = ast
        self.symbol_table = SymbolTable()
        self.errors = []
        self.warnings = []
        self.semantic_tree = None
        self.function_return_stack: List[str] = [] 
    
    def analyze(self) -> Tuple[ASTNode, List[CompileMessage], List[CompileMessage]]:
        self.semantic_tree = self.annotate_node(self.ast)
        return self.semantic_tree, self.errors, self.warnings
    
    def _error(self, message: str, line: Optional[int] = None):
        self.errors.append(CompileMessage(phase="Semantic", message=message, line=line))
    
    def _warn(self, message: str, line: Optional[int] = None):
        self.warnings.append(CompileMessage(phase="Semantic", message=message, line=line))
    
    def annotate_node(self, node: ASTNode) -> ASTNode:
        if node.node_type == "Program":
            annotated = ASTNode("Program", attributes={'scope': 0})
            for child in node.children:
                annotated.children.append(self.annotate_node(child))
            return annotated
        
        elif node.node_type == "Declaration":
            return self.analyze_declaration(node)
        
        elif node.node_type == "FunctionDeclaration":
            return self.analyze_function_declaration(node)
        
        elif node.node_type == "Assignment":
            return self.analyze_assignment(node)
        
        elif node.node_type == "BinaryOp":
            return self.analyze_binary_op(node)
        
        elif node.node_type == "UnaryOp":
            return self.analyze_unary_op(node)
        
        elif node.node_type == "Identifier":
            return self.analyze_identifier(node)
        
        elif node.node_type == "Literal":
            return self.analyze_literal(node)
        
        elif node.node_type == "FunctionCall":
            return self.analyze_function_call(node)
        
        elif node.node_type == "IfStatement":
            return self.analyze_if_statement(node)
        
        elif node.node_type == "WhileStatement":
            return self.analyze_while_statement(node)
        
        elif node.node_type == "ForStatement":
            return self.analyze_for_statement(node)
        
        elif node.node_type == "ReturnStatement":
            return self.analyze_return_statement(node)
        
        elif node.node_type == "Block":
            return self.analyze_block(node)
        
        else:
            annotated = ASTNode(node.node_type, node.value, attributes=node.attributes.copy())
            for child in node.children:
                annotated.children.append(self.annotate_node(child))
            return annotated
    
    def analyze_declaration(self, node: ASTNode) -> ASTNode:
        var_type = node.attributes['type']
        var_name = node.attributes['name']
        line = node.attributes.get('line')
        
        if not self.symbol_table.declare(var_name, 'variable', var_type):
            self._error(f"Variable '{var_name}' already declared in this scope", line)
        
        annotated = ASTNode("Declaration", attributes={
            'type': var_type,
            'name': var_name,
            'scope': self.symbol_table.current_scope,
            'semantic_type': var_type,
            'line': line
        })
        
        if node.children:
            init_expr = self.annotate_node(node.children[0])
            annotated.children.append(init_expr)
            
            expr_type = init_expr.attributes.get('semantic_type')
            if expr_type and not self.types_compatible(var_type, expr_type):
                self._error(f"Type mismatch: cannot assign {expr_type} to {var_type}", line)
            
            self.symbol_table.update_initialization(var_name)
        else:
            self._warn(f"Variable '{var_name}' declared but not initialized", line)
        
        return annotated
    
    def analyze_function_declaration(self, node: ASTNode) -> ASTNode:
        func_type = node.attributes['type']
        func_name = node.attributes['name']
        params = node.attributes.get('params', [])
        line = node.attributes.get('line')
        
        if not self.symbol_table.declare(func_name, 'function', func_type, params):
            self._error(f"Function '{func_name}' already declared", line)
        
        self.symbol_table.enter_scope()
        
        for param in params:
            if not self.symbol_table.declare(param['name'], 'parameter', param['type']):
                self._error(
                    f"Duplicate parameter name '{param['name']}' in function '{func_name}'",
                    param.get('line')
                )
            else:
                self.symbol_table.update_initialization(param['name'])
        
        annotated = ASTNode("FunctionDeclaration", attributes={
            'type': func_type,
            'name': func_name,
            'params': params,
            'scope': self.symbol_table.current_scope - 1,
            'semantic_type': func_type,
            'line': line
        })
        
        self.function_return_stack.append(func_type)
        for child in node.children:
            annotated.children.append(self.annotate_node(child))
        self.function_return_stack.pop()
        
        self.symbol_table.exit_scope()
        
        return annotated
    
    def analyze_assignment(self, node: ASTNode) -> ASTNode:
        line = node.attributes.get('line')
        left = self.annotate_node(node.children[0])
        right = self.annotate_node(node.children[1])
        
        left_type = left.attributes.get('semantic_type')
        right_type = right.attributes.get('semantic_type')
        
        if left_type and right_type and not self.types_compatible(left_type, right_type):
            self._error(f"Type mismatch in assignment: {left_type} = {right_type}", line)
        
        if left.node_type == "Identifier":
            self.symbol_table.update_initialization(left.value)
        
        annotated = ASTNode("Assignment", node.value, [left, right], attributes={
            'semantic_type': left_type or 'unknown',
            'line': line
        })
        
        return annotated
    
    def analyze_binary_op(self, node: ASTNode) -> ASTNode:
        line = node.attributes.get('line')
        left = self.annotate_node(node.children[0])
        right = self.annotate_node(node.children[1])
        
        left_type = left.attributes.get('semantic_type')
        right_type = right.attributes.get('semantic_type')
        
        result_type = self.infer_binary_type(node.value, left_type, right_type)
        
        if result_type == 'error':
            self._error(f"Invalid operation {node.value} between {left_type} and {right_type}", line)
            result_type = 'unknown'
        
        annotated = ASTNode("BinaryOp", node.value, [left, right], attributes={
            'semantic_type': result_type,
            'line': line
        })
        
        return annotated
    
    def analyze_unary_op(self, node: ASTNode) -> ASTNode:
        line = node.attributes.get('line')
        operand = self.annotate_node(node.children[0])
        operand_type = operand.attributes.get('semantic_type')
        
        if node.value == '-' and operand_type not in {'int', 'float'}:
            self._error(f"Unary minus requires numeric type, got {operand_type}", line)
        
        if node.value == '!' and operand_type not in {'int', 'bool'}:
            self._error(f"Logical NOT requires boolean type, got {operand_type}", line)
        
        annotated = ASTNode("UnaryOp", node.value, [operand], attributes={
            'semantic_type': operand_type or 'unknown',
            'line': line
        })
        
        return annotated
    
    def analyze_identifier(self, node: ASTNode) -> ASTNode:
        line = node.attributes.get('line')
        symbol = self.symbol_table.lookup(node.value)
        
        if not symbol:
            self._error(f"Undefined identifier '{node.value}'", line)
            return ASTNode("Identifier", node.value, attributes={'semantic_type': 'unknown', 'line': line})
        
        if not symbol.is_initialized:
            self._warn(f"Variable '{node.value}' used before initialization", line)
        
        return ASTNode("Identifier", node.value, attributes={
            'semantic_type': symbol.value_type or 'unknown',
            'scope': symbol.scope,
            'symbol_type': symbol.symbol_type,
            'line': line
        })
    
    def analyze_literal(self, node: ASTNode) -> ASTNode:
        lit_type = node.attributes.get('type', 'unknown')
        
        if lit_type == 'number':
            if '.' in str(node.value):
                semantic_type = 'float'
            else:
                semantic_type = 'int'
        else:
            semantic_type = lit_type
        
        return ASTNode("Literal", node.value, attributes={
            'type': lit_type,
            'semantic_type': semantic_type,
            'line': node.attributes.get('line')
        })
    
    def analyze_function_call(self, node: ASTNode) -> ASTNode:
        func_name = node.value
        line = node.attributes.get('line')
        symbol = self.symbol_table.lookup(func_name)
        
        if not symbol:
            self._error(f"Undefined function '{func_name}'", line)
            return ASTNode("FunctionCall", func_name, attributes={'semantic_type': 'unknown', 'line': line})
        
        if symbol.symbol_type != 'function':
            self._error(f"'{func_name}' is not a function", line)
        
        annotated = ASTNode("FunctionCall", func_name, attributes={
            'semantic_type': symbol.value_type or 'unknown',
            'scope': symbol.scope,
            'line': line
        })
        
        args = [self.annotate_node(child) for child in node.children]
        annotated.children.extend(args)
        
        if symbol.symbol_type == 'function' and symbol.params is not None:
            expected = symbol.params
            if len(args) != len(expected):
                self._error(
                    f"Function '{func_name}' expects {len(expected)} argument(s) but got {len(args)}",
                    line
                )
            else:
                for i, (arg, param) in enumerate(zip(args, expected), start=1):
                    arg_type = arg.attributes.get('semantic_type')
                    param_type = param['type']
                    if arg_type and not self.types_compatible(arg_type, param_type):
                        self._error(
                            f"Argument {i} of '{func_name}' expects '{param_type}' but got '{arg_type}'",
                            line
                        )
        
        return annotated
    
    def analyze_if_statement(self, node: ASTNode) -> ASTNode:
        condition = self.annotate_node(node.children[0])
        
        annotated = ASTNode("IfStatement", attributes={'scope': self.symbol_table.current_scope})
        annotated.children.append(condition)
        
        self.symbol_table.enter_scope()
        then_block = self.annotate_node(node.children[1])
        annotated.children.append(then_block)
        self.symbol_table.exit_scope()
        
        if len(node.children) > 2:
            self.symbol_table.enter_scope()
            else_block = self.annotate_node(node.children[2])
            annotated.children.append(else_block)
            self.symbol_table.exit_scope()
        
        return annotated
    
    def analyze_while_statement(self, node: ASTNode) -> ASTNode:
        condition = self.annotate_node(node.children[0])
        
        annotated = ASTNode("WhileStatement", attributes={'scope': self.symbol_table.current_scope})
        annotated.children.append(condition)
        
        self.symbol_table.enter_scope()
        body = self.annotate_node(node.children[1])
        annotated.children.append(body)
        self.symbol_table.exit_scope()
        
        return annotated
    
    def analyze_for_statement(self, node: ASTNode) -> ASTNode:
        annotated = ASTNode("ForStatement", attributes={'scope': self.symbol_table.current_scope})
        
        self.symbol_table.enter_scope()
        
        for child in node.children:
            annotated.children.append(self.annotate_node(child))
        
        self.symbol_table.exit_scope()
        
        return annotated
    
    def analyze_return_statement(self, node: ASTNode) -> ASTNode:
        line = node.attributes.get('line')
        annotated = ASTNode("ReturnStatement", attributes={
            'scope': self.symbol_table.current_scope, 'line': line
        })
        
        expected_type = self.function_return_stack[-1] if self.function_return_stack else None
        
        if node.children:
            return_expr = self.annotate_node(node.children[0])
            annotated.children.append(return_expr)
            actual_type = return_expr.attributes.get('semantic_type')
            annotated.attributes['semantic_type'] = actual_type
            
            if expected_type == 'void':
                self._error("Function declared 'void' cannot return a value", line)
            elif expected_type and actual_type and not self.types_compatible(expected_type, actual_type):
                self._error(
                    f"Return type mismatch: function expects '{expected_type}' but got '{actual_type}'",
                    line
                )
        else:
            annotated.attributes['semantic_type'] = 'void'
            if expected_type and expected_type != 'void':
                self._error(f"Missing return value: function expects '{expected_type}'", line)
        
        return annotated
    
    def analyze_block(self, node: ASTNode) -> ASTNode:
        annotated = ASTNode("Block", attributes={'scope': self.symbol_table.current_scope})
        
        for child in node.children:
            annotated.children.append(self.annotate_node(child))
        
        return annotated
    
    def types_compatible(self, type1: str, type2: str) -> bool:
        if type1 == type2:
            return True
        
        if type1 in {'int', 'float'} and type2 in {'int', 'float'}:
            return True
        
        return False
    
    def infer_binary_type(self, op: str, left_type: Optional[str], right_type: Optional[str]) -> str:
        if not left_type or not right_type:
            return 'unknown'
        
        if op in {'+', '-', '*', '/'}:
            if left_type in {'int', 'float'} and right_type in {'int', 'float'}:
                if left_type == 'float' or right_type == 'float':
                    return 'float'
                return 'int'
            return 'error'
        
        if op in {'==', '!=', '<', '>', '<=', '>='}:
            if self.types_compatible(left_type, right_type):
                return 'int'
            return 'error'
        
        if op in {'&&', '||'}:
            return 'int'
        
        return 'unknown'


def ast_to_dict(node: ASTNode) -> Dict:
    return {
        'node_type': node.node_type,
        'value': node.value,
        'attributes': node.attributes,
        'children': [ast_to_dict(child) for child in node.children]
    }


def format_node_label(node: ASTNode) -> str:
    node_type = node.node_type
    attrs = node.attributes

    if node_type == "Declaration":
        return f"Declaration ({attrs.get('type')} {attrs.get('name')})"

    if node_type == "FunctionDeclaration":
        params = attrs.get('params', [])
        param_str = ", ".join(f"{p['type']} {p['name']}" for p in params)
        return f"FunctionDeclaration ({attrs.get('type')} {attrs.get('name')}({param_str}))"

    if node_type in {"BinaryOp", "UnaryOp", "Assignment"}:
        return f"{node_type} ({node.value})"

    if node_type == "Identifier":
        return f"Identifier ({node.value})"

    if node_type == "Literal":
        lit_type = attrs.get('type', '')
        return f"Literal ({node.value}: {lit_type})" if lit_type else f"Literal ({node.value})"

    if node_type == "FunctionCall":
        return f"FunctionCall ({node.value})"

    if node.value not in (None, ''):
        return f"{node_type} ({node.value})"

    return node_type


def print_ast_tree(node: ASTNode, prefix: str = "", is_last: bool = True, is_root: bool = True) -> None:
    connector = "" if is_root else ("└── " if is_last else "├── ")
    print(prefix + connector + format_node_label(node))

    new_prefix = prefix if is_root else prefix + ("    " if is_last else "│   ")

    child_count = len(node.children)
    for i, child in enumerate(node.children):
        print_ast_tree(child, new_prefix, is_last=(i == child_count - 1), is_root=False)


def analyze_source_code(source_code: str) -> Dict[str, Any]:
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    
    tokens_data = [
        {
            'type': token.type.value,
            'value': token.value,
            'line': token.line,
            'column': token.column
        }
        for token in tokens
    ]
    
    parsable_tokens = [t for t in tokens if t.type != TokenType.COMMENT]
    parser = Parser(parsable_tokens)
    syntax_tree = parser.parse()
    
    semantic_analyzer = SemanticAnalyzer(syntax_tree)
    semantic_tree, semantic_errors, semantic_warnings = semantic_analyzer.analyze()
    
    all_error_messages: List[CompileMessage] = lexer.errors + parser.errors + semantic_errors
    all_warning_messages: List[CompileMessage] = list(semantic_warnings)
    
    def _sort_key(msg: CompileMessage):
        return msg.line if msg.line is not None else float('inf')
    
    all_error_messages.sort(key=_sort_key)
    all_warning_messages.sort(key=_sort_key)
    
    all_errors = [str(m) for m in all_error_messages]
    all_warnings = [str(m) for m in all_warning_messages]
    
    def _details(msgs: List[CompileMessage]) -> List[Dict[str, Any]]:
        return [
            {'phase': m.phase, 'message': m.message, 'line': m.line, 'column': m.column, 'text': str(m)}
            for m in msgs
        ]
    
    return {
        'tokens': tokens_data,
        'syntax_tree': ast_to_dict(syntax_tree),
        'semantic_tree': ast_to_dict(semantic_tree),
        'syntax_tree_node': syntax_tree,      # raw ASTNode, for drawing in the terminal
        'semantic_tree_node': semantic_tree,  # raw ASTNode, for drawing in the terminal
        'lexical_errors': [str(m) for m in lexer.errors],
        'syntax_errors': [str(m) for m in parser.errors],
        'semantic_errors': [str(m) for m in semantic_errors],
        'errors': all_errors,
        'warnings': all_warnings,
        'error_details': _details(all_error_messages),
        'warning_details': _details(all_warning_messages),
        'error_count': len(all_errors),
        'warning_count': len(all_warnings),
        'success': len(all_errors) == 0
    }


def read_source_from_terminal() -> str:
    print("Paste or type your code, then press CTRL+Z then Enter.\n")
    
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    
    return "\n".join(lines).strip()


def main():
    source_code = read_source_from_terminal()

    print("Compiler Analysis System")
    print("=" * 50)
    print("\nSource Code:")
    print(source_code)
    print("\n" + "=" * 50)
    
    result = analyze_source_code(source_code)
    
    print("\n--- LEXICAL ANALYSIS ---")
    print(f"Total Tokens: {len(result['tokens'])}")
    for token in result['tokens']:
        print(f"  {token['type']:15} | {token['value']:15} | Line {token['line']}, Col {token['column']}")
    
    print("\n--- SYNTAX ANALYSIS ---")
    print(f"Syntax Tree Root: {result['syntax_tree']['node_type']}")
    print(f"Top-level Statements: {len(result['syntax_tree']['children'])}")
    print("\nAST Tree:")
    print_ast_tree(result['syntax_tree_node'])
    
    print("\n--- SEMANTIC ANALYSIS ---")
    print(f"Semantic Tree Root: {result['semantic_tree']['node_type']}")
    print(f"Analysis Success: {result['success']}")

    print("\nSemantic Tree (Dictionary Format):")
    print(json.dumps(result['semantic_tree'], indent=4, ensure_ascii=False))


    print("\n--- DIAGNOSTIC REPORT ---")

    print(f"{result['error_count']} error(s), {result['warning_count']} warning(s)")
    
    source_lines = source_code.split('\n')
    
    def print_message(detail: Dict[str, Any]):
        print(f"  - {detail['text']}")
        line_no = detail['line']
        if line_no is not None and 1 <= line_no <= len(source_lines):
            print(f"      {source_lines[line_no - 1]}")
            if detail['column'] is not None:
                print(f"      {' ' * (detail['column'] - 1)}^")
    
    if result['error_details']:
        print("\nErrors (in source order):")
        for detail in result['error_details']:
            print_message(detail)
    
    if result['warning_details']:
        print("\nWarnings (in source order):")
        for detail in result['warning_details']:
            print_message(detail)
    
    print("\n" + "=" * 50)
    print("Analysis Complete!")


if __name__ == "__main__":
    main()


"""
int x = 10;
float y = 20.5;
int z = x + y;

int add(int a, int b) {
    return a + b;
}

int result = add(x, z);

if (result > 20) {
    int temp = result * 2;
}

while (x < 100) {
    x = x + 1;
}








int x;
int x = 10;

y = 5;

bool flag = 3;

int add(int a, int b) {
    return a + c;
}

int z = add(1);

int k;
int m = k + 1;

if (x > ) {
    x = x + 1
}
"""