#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2021 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
"""
Provides chromosome visitors to perform post processing.
"""
import logging
from typing import List

import pynguin.ga.chromosomevisitor as cv
import pynguin.ga.testcasechromosome as tcc
import pynguin.ga.testsuitechromosome as tsc
import pynguin.testcase.statements.statementvisitor as sv
import pynguin.testcase.testcasevisitor as tcv


class ExceptionTruncation(cv.ChromosomeVisitor):
    """Truncates test cases after an exception-raising statement."""

    def visit_test_suite_chromosome(self, chromosome: tsc.TestSuiteChromosome) -> None:
        for test_case_chromosome in chromosome.test_case_chromosomes:
            test_case_chromosome.accept(self)

    def visit_test_case_chromosome(self, chromosome: tcc.TestCaseChromosome) -> None:
        if chromosome.is_failing():
            chop_position = chromosome.get_last_mutatable_statement()
            if chop_position is not None:
                chromosome.test_case.chop(chop_position)


class TestCasePostProcessor(cv.ChromosomeVisitor):
    """Applies all given visitors to the visited test cases."""

    def __init__(self, test_case_visitors: List[tcv.TestCaseVisitor]):
        self._test_case_visitors = test_case_visitors

    def visit_test_suite_chromosome(self, chromosome: tsc.TestSuiteChromosome) -> None:
        for test_case_chromosome in chromosome.test_case_chromosomes:
            test_case_chromosome.accept(self)

    def visit_test_case_chromosome(self, chromosome: tcc.TestCaseChromosome) -> None:
        for visitor in self._test_case_visitors:
            chromosome.test_case.accept(visitor)


# pylint:disable=too-few-public-methods
class UnusedStatementsTestCaseVisitor(tcv.TestCaseVisitor):
    """Removes unused primitive and collections statements."""

    _logger = logging.getLogger(__name__)

    def visit_default_test_case(self, test_case) -> None:
        primitive_remover = UnusedPrimitiveStatementVisitor()
        size_before = test_case.size()
        # Iterate over copy, to be able to modify original.
        for stmt in reversed(list(test_case.statements)):
            stmt.accept(primitive_remover)
        self._logger.debug(
            "Removed %s unused primitives from test case",
            size_before - test_case.size(),
        )


class UnusedPrimitiveStatementVisitor(sv.StatementVisitor):
    """Visits all statements and removes the unused ones.
    Has to visit the statements in reverse order."""

    def __init__(self):
        self._used_references = set()

    def _handle_collection_or_primitive(self, stmt) -> None:
        if stmt.ret_val not in self._used_references:
            stmt.test_case.remove_statement(stmt)

    def _handle_remaining(self, stmt) -> None:
        used = stmt.get_variable_references()
        used.discard(stmt.ret_val)
        self._used_references.update(used)

    def visit_int_primitive_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_float_primitive_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_string_primitive_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_bytes_primitive_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_boolean_primitive_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_enum_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_none_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_constructor_statement(self, stmt) -> None:
        self._handle_remaining(stmt)

    def visit_method_statement(self, stmt) -> None:
        self._handle_remaining(stmt)

    def visit_function_statement(self, stmt) -> None:
        self._handle_remaining(stmt)

    def visit_field_statement(self, stmt) -> None:
        raise NotImplementedError("No field support yet.")

    def visit_assignment_statement(self, stmt) -> None:
        raise NotImplementedError("No field support yet.")

    def visit_list_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_set_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_tuple_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)

    def visit_dict_statement(self, stmt) -> None:
        self._handle_collection_or_primitive(stmt)
