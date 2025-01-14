import io
import sys
import json

import re

class Tokenizer:
    
    def __init__(self, code, debug=False):
        self.code = code
        self.debug = debug
    
    # Define token types and their patterns
    TOKENS = [
        ("COMMENT", r"//[^\n]*|/\*.*?\*/"),  # Single-line and multi-line comments
        ("KEYWORD", r"कार्य मुख्यः|चरः|मुद्रणम्|यदि|अन्यथा यदि|अन्यथा|यावद्‌|अनुवर्तते|विरमतु|कार्य|प्रतिददाति"),  # Keywords
        ("LOGICAL_OPERATOR", r"&&|\|\|"),  # Logical operators (AND, OR)
        ("BINARY_OPERATOR", r"==|<=|>=|<|>|!="),  # Comparison operators
        ("ASSIGNMENT_OPERATOR", r"=|\+=|-=|\*=|/=|%="),  # Assignment operators
        ("BINARY_OPERATOR", r"\+|-|\*|/|%"),  # Arithmetic operators
        ("BOOLEAN", r"सत्य|असत्य"),  # Boolean literals
        ("NULL", r"रिक्त"),  # Null literal
        ("IDENTIFIER", r"[अ-हa-zA-Z\u0900-\u097F]+(?:[अ-हa-zA-Z0-9_])*"),  # Identifiers (including Devanagari characters)
        ("FLOAT", r"[0-9]+\.[0-9]+"),  # Floating-point numbers
        ("NUMBER", r"[0-9]+"),  # Integer numbers
        ("STRING", r"\"(\\.|[^\\\"])*\""),  # String literals
        ("PUNCTUATION", r"[{}();,]"),  # Punctuation characters
        ("WHITESPACE", r"\s+"),  # Whitespace (spaces, tabs, newlines)
    ]

    # Pre-compile all token patterns for performance
    TOKEN_REGEX = [(token_type, re.compile(pattern, re.DOTALL)) for token_type, pattern in TOKENS]

    def tokenize(self):
        """
        Tokenizes the input self.code into a list of tokens.

        :param self.code: The input self.code as a string.
        :param self.debug: If True, prints self.debug information during tokenization.
        :return: A list of (token_type, value, line, column) tuples.
        """
        tokens = []
        line = 1
        column = 1

        while self.code:
            match = None
            for token_type, regex in Tokenizer.TOKEN_REGEX:
                match = regex.match(self.code)
                if match:
                    value = match.group(0)

                    # Handle comments: skip adding them to the token list
                    if token_type == "COMMENT":
                        if self.debug:
                            print(f"Ignored {token_type}: '{value}' at line {line}, column {column}")

                    # Handle other token types: add them to the token list (skip whitespace)
                    elif token_type != "WHITESPACE":
                        tokens.append((token_type, value, line, column))

                    if self.debug and token_type != "COMMENT":
                        print(f"Matched {token_type}: '{value}' at line {line}, column {column}")

                    # Update self.code, column, and line positions
                    self.code = self.code[match.end():]
                    column += match.end()

                    # Adjust line and column for multi-line tokens
                    if '\n' in value:
                        line += value.count('\n')
                        column = len(value.split('\n')[-1]) + 1
                    break

            # Raise an error if no token matches the current self.code
            if not match:
                return {"type":"TokenizerOutput",
                        "response": False,
                        "message": f"Unexpected character '{self.code[0]}' at line {line}, column {column}. Context: {self.code[:20]}...",
                        "tokens": []}


        return {"type":"TokenizerOutput",
                "response": True,
                "message": f"Tokenization successful.",
                "tokens": tokens}


class Parser:
    def __init__(self, tokens, debug=False):
        self.tokens = tokens
        self.pos = 0
        self.debug = debug

    def current(self):
        # Return the current token if within bounds, else None
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, token_type=None):
        # Consume and return the current token, optionally verifying its type
        token = self.current()

        if self.debug:
            print(f"Consuming token: {token}")

        if token is None:
            raise SyntaxError("Unexpected end of input")
        if token_type and token[0] != token_type:
            raise SyntaxError(f"Expected {token_type}, got {token[0]} at position {self.pos}")

        self.pos += 1
        return token

    def parse_program(self):
        # Parse the program as a series of statements
        body = []

        try:
            while self.current():
                statement = self.parse_statement()
                if statement:
                    body.append(statement)
        except SyntaxError as e:
            return {"type" : "ParserOutput", "response": False, "message": str(e), "AST" : {"type": "SanskritProgram", "body": []}}

        return {"type" : "ParserOutput", "response": True, "message": "Parsing successful.", "AST" : {"type": "SanskritProgram", "body": body}}

    def parse_statement(self):
        # Determine the type of statement and parse accordingly
        token = self.current()
        if token and token[0] == "KEYWORD":
            keyword = token[1]
            if keyword == "कार्य मुख्यः":
                return self.parse_main_function()
            elif keyword == "कार्य":
                return self.parse_function_defination()
            elif keyword == "प्रतिददाति":
                return self.parse_return_statement()
            elif keyword == "चरः":
                return self.parse_variable_declaration()
            elif keyword == "मुद्रणम्":
                return self.parse_print_statement()
            elif keyword == "यदि":
                return self.parse_if_statement()
            elif keyword == "यावद्‌":
                return self.parse_while_statement()
            elif keyword == "विरमतु":
                return self.parse_break_statement()
            elif keyword == "अनुवर्तते":
                return self.parse_continue_statement()
        elif token and token[0] == "IDENTIFIER":
            # Determine if the identifier is part of a function call or an assignment
            next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            statement = None
            if next_token and next_token[1] == "(":
                statement = self.parse_function_call()  # Parse function call
                self.consume("PUNCTUATION")  # Consume the semicolon
                return statement
            else:
                statement = self.parse_assignment_expression()  # Parse assignment
                self.consume("PUNCTUATION")  # Consume the semicolon
                return statement

        raise SyntaxError(f"Unexpected token {token} in statement")
    
    def parse_code_block(self): 
        # Parse a block of code enclosed in curly braces
        body = []

        self.consume("PUNCTUATION")  # Consume the opening curly brace "{"
        while self.current() and self.current()[1] != "}":
            statement = self.parse_statement()
            if statement:
                body.append(statement)
        self.consume("PUNCTUATION")  # Consume the closing curly brace "}"
        
        return {
            "type": "BlockStatement",
            "body": body
        }

    def parse_main_function(self):
        # Parse the main function block

        self.consume("KEYWORD")  # Consume "मुख्यः"
        self.consume("PUNCTUATION")  # Consume "("
        self.consume("PUNCTUATION")  # Consume ")"

        body = self.parse_code_block()
        
        return {
            "type": "MainFunction",
            "id":  {
                "type": "IdentifierExpression",
                "name": "मुख्यः"
            },
            "parameters": [],
            "body": body
        }

    def parse_function_defination(self):
        # Parse a function definition
        self.consume("KEYWORD")  # Consume "कार्य"
        identifier_token = self.consume("IDENTIFIER")[1]

        self.consume("PUNCTUATION")  # Consume "("
        parameters = None
        if self.current() and self.current()[1] != ")":
            parameters = self.parse_expression_list()
        self.consume("PUNCTUATION")  # Consume ")"

        body = self.parse_code_block()

        return {
            "type": "FunctionDefination",
            "id":  {
                "type": "IdentifierExpression",
                "name": identifier_token
            },
            "parameters": parameters,
            "body": body
        }

    def parse_function_call(self):
        # Parse a function call expression
        identifier_token = self.consume("IDENTIFIER")[1]
        self.consume("PUNCTUATION")  # Consume "("

        arguments = []
        if self.current() and self.current()[1] != ")":
            arguments = self.parse_expression_list()

        self.consume("PUNCTUATION")  # Consume ")"
        return {
            "type": "FunctionCall",
            "callee": {
                "type": "IdentifierExpression",
                "name": identifier_token
            },
            "arguments": arguments
        }

    def parse_return_statement(self):
        # Parse a return statement
        self.consume("KEYWORD")  # Consume "प्रतिददाति"
        expression = self.parse_expression()
        self.consume("PUNCTUATION")  # Consume the semicolon
        return {"type": "ReturnStatement", "argument": expression}

    def parse_variable_declaration(self):
        # Parse a variable declaration
        self.consume("KEYWORD")  # Consume "चरः"

        identifier_token = self.consume("IDENTIFIER")[1]  # Parse the identifier

        self.consume("ASSIGNMENT_OPERATOR")  # Consume the "=" operator

        initializer_token = self.parse_expression()  # Parse the initializer expression

        self.consume("PUNCTUATION")  # Consume the semicolon

        return {
            "type": "VariableDeclaration",
            "id":  {
                "type": "IdentifierExpression",
                "name": identifier_token
            },
            "init": initializer_token
        }
        
    def parse_if_statement(self):
        # Consume the "यदि" keyword for "if"
        self.consume("KEYWORD")  # Consume "यदि"

        # Consume the opening parenthesis "("
        self.consume("PUNCTUATION")  # Consume "("

        # Parse the test condition (expression)
        test = self.parse_expression()

        # Consume the closing parenthesis ")"
        self.consume("PUNCTUATION")  # Consume ")"

        body = self.parse_code_block()

        # Now handle the else-if and else clauses
        alternates = []
        while self.current() and self.current()[1] == "अन्यथा यदि":  # "else if" case
            alternates.append(self.parse_else_if_statement())

        if self.current() and self.current()[1] == "अन्यथा":  # "else" case
            alternates.append(self.parse_else_statement())

        # Return the AST node for the if statement
        return {
            "type": "IfStatement",
            "test": test,
            "body" : body,
            "alternates": alternates
        }

    def parse_else_if_statement(self):
        # Consume the "अन्यथा यदि" keyword for "else if"
        self.consume("KEYWORD")  # Consume "अन्यथा यदि"

        # Consume the opening parenthesis "("
        self.consume("PUNCTUATION")  # Consume "("

        # Parse the test condition (expression)
        test = self.parse_expression()

        # Consume the closing parenthesis ")"
        self.consume("PUNCTUATION")  # Consume ")"

        body = self.parse_code_block()

        # Return the AST node for the else if statement
        return {
            "type": "IfStatement",
            "test": test,
            "body" : body,
            "alternates": []
        }
        
    def parse_else_statement(self):
        # Consume the "अन्यथा" keyword for "else"
        self.consume("KEYWORD")  # Consume "अन्यथा"

        body = self.parse_code_block()

        # Return the AST node for the else statement
        return {
            "type": "ElseStatement",
            "body": body
        }

    def parse_while_statement(self):
        # Consume the "यावद्‌" keyword
        self.consume("KEYWORD")
    
        # Consume the opening parenthesis "("
        self.consume("PUNCTUATION")
    
        # Parse the test expression (e.g., the condition inside the while loop)
        test_expression = self.parse_expression()
    
        # Consume the closing parenthesis ")"
        self.consume("PUNCTUATION")
    
        body = self.parse_code_block()
    
        # Return the structured JSON for the while statement
        return {
            "type": "WhileStatement",
            "test": test_expression,
            "body": body
        }


    def parse_break_statement(self):
        self.consume("KEYWORD")  # Expect "विरमतु"
        self.consume("PUNCTUATION")  # Expect ";"
        return {"type": "BreakStatement"}

    def parse_continue_statement(self):
        self.consume("KEYWORD")  # Expect "अनुवर्तते"
        self.consume("PUNCTUATION")  # Expect ";"
        return {"type": "ContinueStatement"}

    def parse_print_statement(self):
        # Consume the "मुद्रणम्" keyword
        self.consume("KEYWORD")  # Consume "मुद्रणम्"

        # Consume the opening parenthesis "("
        self.consume("PUNCTUATION")  # Consume "("

        # Parse the arguments
        arguments = None
        if self.current() and self.current()[1] != ")":
            arguments = self.parse_expression_list()

        # Consume the closing parenthesis ")"
        self.consume("PUNCTUATION")  # Consume ")"

        # Consume the semicolon ";"
        self.consume("PUNCTUATION")  # Consume ";"

        # Return the AST node
        return {
            "type": "PrintStatement",
            "arguments": arguments
        }
        
    def parse_expression_list(self):
        expressions = [self.parse_expression()]  # Parse the first expression

        # Parse additional expressions separated by commas
        while self.current() and self.current()[1] == ",":
            self.consume("PUNCTUATION")  # Consume ","
            expressions.append(self.parse_expression())

        return expressions
    
    def parse_expression(self):
        # Parse the left-hand side expression
        left = self.parse_primary_expression()

        # Check if the next token is a logical operator
        while self.current() and (self.current()[0] == "BINARY_OPERATOR" or self.current()[0] == "LOGICAL_OPERATOR"):
            if self.current()[0] == "LOGICAL_OPERATOR":
                operator = self.consume("LOGICAL_OPERATOR")[1]  # Consume the logical operator
                right = self.parse_expression()  # Parse the right-hand side expression

                # Construct a LogicalExpression node
                left = {
                    "type": "LogicalExpression",
                    "operator": operator,
                    "left": left,
                    "right": right
                }
            elif self.current()[0] == "BINARY_OPERATOR":
                operator = self.consume("BINARY_OPERATOR")[1]  # Consume the binary operator
                right = self.parse_primary_expression()  # Parse the right-hand side expression

                # Construct a BinaryExpression node
                left = {
                    "type": "BinaryExpression",
                    "operator": operator,
                    "left": left,
                    "right": right
                }

        return left


    def parse_primary_expression(self):
        token = self.current()

        if token[0] == "IDENTIFIER":
            # Check if the next token is a parenthesis indicating a function call
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1][1] == "(":
                return self.parse_function_call()  # Parse as a function call
            # Otherwise, treat it as an identifier expression
            return {
                "type": "IdentifierExpression",
                "name": self.consume("IDENTIFIER")[1]
            }
        elif token[0] == "NUMBER":
            # Consume the number
            return {
                "type": "NumericLiteral",
                "value": int(self.consume("NUMBER")[1])
            }
        elif token[0] == "FLOAT":
            # Consume the float
            return {
                "type": "FloatLiteral",
                "value": float(self.consume("FLOAT")[1])
            }
        elif token[0] == "STRING":
            # Consume the string
            return {
                "type": "StringLiteral",
                "value": self.consume("STRING")[1]
            }
        elif token[0] == "BOOLEAN":
            # Consume the boolean
            return {
                "type": "BooleanLiteral",
                "value": self.consume("BOOLEAN")[1] == "सत्य"
            }
        elif token[0] == "NULL":
            #consume null
            self.consume("NULL")
            return{
                "type": "Null",
                "value": None
            }
        elif token[1] == "(":
            # Handle parenthesized expressions
            self.consume("PUNCTUATION")  # Consume "("
            expression = self.parse_expression()
            self.consume("PUNCTUATION")  # Consume ")"
            return expression
        else:
            raise SyntaxError(f"Unexpected token: {token}")

    def parse_assignment_expression(self):
        # Parse the left-hand side expression (which could be an identifier)
        left = self.parse_primary_expression()

        # Check if the next token is an assignment operator (e.g., '=', '+=', '-=')
        if self.current() and self.current()[0] == "ASSIGNMENT_OPERATOR":
            operator = self.consume("ASSIGNMENT_OPERATOR")[1]  # Consume the assignment operator
            right = self.parse_expression()  # Parse the right-hand side expression

            # Construct the assignment expression node
            return {
                "type": "AssignmentExpression",
                "operator": operator,
                "left": left,
                "right": right
            }   

        # If no assignment operator, return the left expression (could be a simple variable or value)
        return left
    
    
    
class ASTValidator:
    def __init__(self,ast, debug=False):
        self.ast = ast
        self.debug = debug
        self.errors = []
        self.global_variables = set()
        self.function_definitions = set()
        self.current_function_scope = None
        self.local_variables = {}

    def validate(self):
        """Entry point for validating the AST."""
        self.errors.clear()
        self.global_variables.clear()
        self.function_definitions.clear()
        self.local_variables.clear()
        self.current_function_scope = None

        self._collect_definitions(self.ast)
        
        self._validate_node(self.ast)
        return {"type" : "ValidatorOutput", "response": not self.errors, "errors": self.errors}
    
    def _collect_definitions(self, node):
        """Collect all function definitions and global variables."""
        if node["type"] == "SanskritProgram":
            if "body" not in node or not isinstance(node["body"], list):
                self.errors.append("SanskritProgram must have a 'body' of type list.")
            for child in node.get("body", []):
                self._collect_definitions(child)
        elif node["type"] == "FunctionDefination" or node["type"] == "MainFunction":
            function_name = node["id"]["name"]
            if function_name in self.function_definitions:
                self.errors.append(f"Function '{function_name}' is already defined.")
            else:
                self.function_definitions.add(function_name)
        elif node["type"] == "VariableDeclaration":
            variable_name = node["id"]["name"]
            if self.current_function_scope is None:
                # Global variable
                if variable_name in self.global_variables:
                    self.errors.append(f"Global variable '{variable_name}' is already defined.")
                self.global_variables.add(variable_name)
        else:
            self.errors.append(f"Unknown node type outside main: {node['type']}")

    def _validate_node(self, node):
        """Recursive validation of an AST node."""
        node_type = node.get("type")
        if self.debug:
            print(f"Validating node: {node_type}")

        if node_type == "SanskritProgram":
            self._validate_program(node)
        elif node_type == "MainFunction":
            self._validate_main_function(node)
        elif node_type == "FunctionDefination":
            self._validate_function_definition(node)
        elif node_type == "BlockStatement":
            self._validate_block_statement(node)
        elif node_type == "VariableDeclaration":
            self._validate_variable_declaration(node)
        elif node_type == "AssignmentExpression":
            self._validate_assignment_expression(node)
        elif node_type == "BinaryExpression":
            self._validate_binary_expression(node)
        elif node_type == "LogicalExpression":
            self._validate_logical_expression(node)
        elif node_type == "IfStatement":
            self._validate_if_statement(node)
        elif node_type == "ElseStatement":
            self._else_statement(node)
        elif node_type == "WhileStatement":
            self._validate_while_statement(node)
        elif node_type == "FunctionCall":
            self._validate_function_call(node)
        elif node_type == "PrintStatement":
            self._validate_print_statement(node)
        elif node_type in {"BreakStatement", "ContinueStatement", "ReturnStatement"}:
            self._validate_simple_statement(node)
        else:
            self.errors.append(f"Unknown node type: {node_type}")

    def _validate_program(self, node):
        if "body" not in node or not isinstance(node["body"], list):
            self.errors.append("SanskritProgram must have a 'body' of type list.")
        for child in node.get("body", []):
            if child["type"] == "FunctionDefination" or child["type"] == "MainFunction":
                self._validate_node(child)

    def _validate_main_function(self, node):
        if "id" not in node or node["id"].get("name") != "मुख्यः":
            self.errors.append("mainFunction must have an id with the name 'मुख्यः'.")
        self.current_function_scope = "मुख्यः"
        self.local_variables[self.current_function_scope] = set()
        
        for param in node.get("parameters", []):
            if param["type"] != "IdentifierExpression":
                self.errors.append("Function parameter must have a name.")
            if "name" not in param:
                self.errors.append("Function parameter must have a name.")
            param_name = param["name"]
            if param_name in self.global_variables:
                self.errors.append(f"Parameter '{param_name}' is already defined as globle variable'.")
            self.local_variables[function_name].add(param_name)
        
        self._validate_node(node.get("body", {}))
        self.current_function_scope = None

    def _validate_function_definition(self, node):
        if "id" not in node or "name" not in node["id"]:
            self.errors.append("FunctionDefination must have a valid id.")
        if "body" not in node:
            self.errors.append("FunctionDefination must have a body.")
        function_name = node["id"]["name"]
        self.current_function_scope = function_name
        self.local_variables[function_name] = set()
        
        for param in node.get("parameters", []):
            if param["type"] != "IdentifierExpression":
                self.errors.append("Function parameter must have a name.")
            if "name" not in param:
                self.errors.append("Function parameter must have a name.")
            param_name = param["name"]
            if param_name in self.global_variables:
                self.errors.append(f"Parameter '{param_name}' is already defined as globle variable.")
            self.local_variables[function_name].add(param_name)
        
        self._validate_node(node.get("body", {}))
        self.current_function_scope = None
        
    def _validate_block_statement(self, node):
        if "body" not in node or not isinstance(node["body"], list):
            self.errors.append("BlockStatement must have a 'body' of type list.")
        for child in node.get("body", []):
            self._validate_node(child)

    def _validate_variable_declaration(self, node):
        if "id" not in node or "name" not in node["id"]:
            self.errors.append("VariableDeclaration must have a valid id.")
        if "init" not in node:
            self.errors.append("VariableDeclaration must have an initializer.")

        variable_name = node["id"]["name"]
        if self.current_function_scope:
            if variable_name in self.local_variables[self.current_function_scope]:
                self.errors.append(f"Variable '{variable_name}' is already defined in function '{self.current_function_scope}'.")
            self.local_variables[self.current_function_scope].add(variable_name)
        else:
            if variable_name in self.global_variables:
                self.errors.append(f"Global variable '{variable_name}' is already defined.")
            self.global_variables.add(variable_name)

    def _validate_assignment_expression(self, node):
        if "operator" not in node or node["operator"] not in {"=", "+=", "-=", "*=", "/=", "%="}:
            self.errors.append("Invalid operator in AssignmentExpression.")
        if "left" not in node or "right" not in node:
            self.errors.append("AssignmentExpression must have 'left' and 'right'.")
            
        variable_name = node["left"]["name"]
        if self.current_function_scope:
            if variable_name not in self.local_variables[self.current_function_scope]:
                self.errors.append(f"Variable '{variable_name}' is not defined in function '{self.current_function_scope}'.")
        elif variable_name not in self.global_variables:
            self.errors.append(f"Global variable '{variable_name}' is not defined.")

    def _validate_binary_expression(self, node):
        if "operator" not in node or node["operator"] not in {"+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">="}:
            self.errors.append("Invalid operator in BinaryExpression.")
        if "left" not in node or "right" not in node:
            self.errors.append("BinaryExpression must have 'left' and 'right'.")

    def _validate_logical_expression(self, node):
        if "operator" not in node or node["operator"] not in {"||", "&&"}:
            self.errors.append("Invalid operator in LogicalExpression.")
        if "left" not in node or "right" not in node:
            self.errors.append("LogicalExpression must have 'left' and 'right'.")

    def _validate_if_statement(self, node):
        if "test" not in node or "body" not in node:
            self.errors.append("IfStatement must have 'test' and 'body'.")
        self._validate_node(node.get("body", {}))
        for alternate in node.get("alternates", []):
            self._validate_node(alternate)
            
    def _else_statement(self, node):
        if "body" not in node:
            self.errors.append("ElseStatement must have a 'body'.")
        self._validate_node(node.get("body", {}))

    def _validate_while_statement(self, node):
        if "test" not in node or "body" not in node:
            self.errors.append("WhileStatement must have 'test' and 'body'.")
        self._validate_node(node.get("body", {}))

    def _validate_function_call(self, node):
        if "callee" not in node or "name" not in node["callee"]:
            self.errors.append("FunctionCall must have a valid callee.")
        if "arguments" not in node or not isinstance(node["arguments"], list):
            self.errors.append("FunctionCall must have arguments of type list.")
            
        function_name = node["callee"]["name"]
        if function_name not in self.function_definitions:
            self.errors.append(f"Function '{function_name}' is not defined.")

    def _validate_print_statement(self, node):
        if "arguments" not in node or not isinstance(node["arguments"], list):
            self.errors.append("PrintStatement must have arguments of type list.")

    def _validate_simple_statement(self, node):
        if "type" not in node:
            self.errors.append(f"Invalid simple statement: {node}")
            
            
class CodeGenerator:
    def __init__(self, ast):
        self.ast = ast
        self.indent_level = 0

    def generate(self):
        code = self._generate_node(self.ast)
        # Append main() call at the end of the code
        code += "\nmain()"
        return code

    def _indent(self):
        return "    " * self.indent_level

    def _generate_block(self, statements):
        # Generate code for a block of statements with proper indentation
        self.indent_level += 1
        code = "\n".join(self._indent() + self._generate_node(stmt) for stmt in statements)
        self.indent_level -= 1
        return code

    def _generate_node(self, node):
        if node["type"] == "SanskritProgram":
            return "\n".join(self._generate_node(stmt) for stmt in node["body"])
        elif node["type"] == "VariableDeclaration":
            return f"{node['id']['name']} = {self._generate_node(node['init'])}"
        elif node["type"] == "MainFunction":
            body = self._generate_block(node["body"]["body"])
            return f"def main():\n{body}"
        elif node["type"] == "NumericLiteral":
            return str(node["value"])
        elif node["type"] == "FloatLiteral":
            return str(node["value"])
        elif node["type"] == "BooleanLiteral":
            return "True" if node["value"] else "False"
        elif node["type"] == "StringLiteral":
            return str(node["value"])
        elif node["type"] == "Null":
            return "None"
        elif node["type"] == "IdentifierExpression":
            return node["name"]
        elif node["type"] == "PrintStatement":
            args = ", ".join(self._generate_node(arg) for arg in node["arguments"])
            return f"print({args})"
        elif node["type"] == "IfStatement":
            test = self._generate_node(node["test"])
            body = self._generate_block(node["body"]["body"])
            code = f"if {test}:\n{body}"
    
            # Handle elif and else
            for alternate in node.get("alternates", []):
                if alternate["type"] == "IfStatement":
                    test = self._generate_node(alternate["test"])
                    body = self._generate_block(alternate["body"]["body"])
                    code += f"\n{self._indent()}elif {test}:\n{body}"
                elif alternate["type"] == "ElseStatement":
                    body = self._generate_block(alternate["body"]["body"])
                    code += f"\n{self._indent()}else:\n{body}"
            return code

        elif node["type"] == "BinaryExpression":
            left = self._generate_node(node["left"])
            right = self._generate_node(node["right"])
            return f"{left} {node['operator']} {right}"
        elif node["type"] == "WhileStatement":
            test = self._generate_node(node["test"])
            body = self._generate_block(node["body"]["body"])
            return f"while {test}:\n{body}"
        elif node["type"] == "AssignmentExpression":
            left = self._generate_node(node["left"])
            right = self._generate_node(node["right"])
            return f"{left} {node['operator']} {right}"
        elif node["type"] == "FunctionCall":
            callee = self._generate_node(node["callee"])
            args = ", ".join(self._generate_node(arg) for arg in node["arguments"])
            return f"{callee}({args})"
        elif node["type"] == "FunctionDefination":
            params = ", ".join(param["name"] for param in node["parameters"])
            body = self._generate_block(node["body"]["body"])
            return f"def {node['id']['name']}({params}):\n{body}"
        elif node["type"] == "ReturnStatement":
            return f"return {self._generate_node(node['argument'])}"
        elif node["type"] == "LogicalExpression":
            left = self._generate_node(node["left"])
            right = self._generate_node(node["right"])
            operator = "or" if node["operator"] == "||" else "and"
            return f"{left} {operator} {right}"
        elif node["type"] == "BreakStatement":
            return "break"
        elif node["type"] == "ContinueStatement":
            return "continue"
        else:
            raise ValueError(f"Unknown node type: {node['type']}")


# Function to execute Python code and capture its output
def capture_exec_output(python_code):
    captured_output = io.StringIO()
    original_stdout = sys.stdout

    try:
        sys.stdout = captured_output  # Redirect output
        exec(python_code, {})  # Use an isolated environment
    except Exception as e:
        captured_output.write(f"Error: {e}")
    finally:
        sys.stdout = original_stdout  # Restore original stdout

    return captured_output.getvalue()


# Main function to process Sanskrit code
def process_sanskrit_code(code):
    try:
        # Tokenize
        tokenizer = Tokenizer(code, debug=False)
        tokenizer_output = tokenizer.tokenize()

        if not tokenizer_output["response"]:
            return json.dumps({"error": tokenizer_output["message"]}, ensure_ascii=False)

        # Parse
        parser = Parser(tokenizer_output["tokens"], debug=False)
        parser_output = parser.parse_program()

        if not parser_output["response"]:
            return json.dumps({"error": parser_output["message"]}, ensure_ascii=False)

        # Validate
        validator = ASTValidator(parser_output["AST"], debug=False)
        validator_output = validator.validate()

        if not validator_output["response"]:
            return json.dumps({"error": validator_output["errors"]}, ensure_ascii=False)

        # Generate Python code
        codegen = CodeGenerator(parser_output["AST"])
        python_code = codegen.generate()

        # Execute the Python code and capture the output
        programme_output = capture_exec_output(python_code)

        # Return all results as JSON
        output = {
            "type": "CompilerOutput",
            "output": [
                tokenizer_output,
                parser_output,
                validator_output,
                {"type": "PythonCode", "code": python_code},
                {"type": "ProgrammeOutput", "output": programme_output},
            ],
        }
        return json.dumps(output, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)
