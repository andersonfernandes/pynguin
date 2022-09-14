#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2022 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
import ast
import importlib
import inspect
import threading
from unittest.mock import MagicMock

import pytest

import pynguin.configuration as config
import pynguin.ga.testcasechromosome as tcc
import pynguin.ga.testsuitechromosome as tsc
from pynguin.analyses.constants import EmptyConstantProvider
from pynguin.analyses.module import generate_test_cluster
from pynguin.analyses.seeding import AstToTestCaseTransformer
from pynguin.analyses.typesystem import InferredSignature
from pynguin.ga.computations import (
    TestCaseStatementCheckedCoverageFunction,
    TestSuiteStatementCheckedCoverageFunction,
)
from pynguin.instrumentation.machinery import install_import_hook
from pynguin.slicer.dynamicslicer import DynamicSlicer
from pynguin.slicer.statementslicingobserver import StatementSlicingObserver
from pynguin.testcase.execution import ExecutionTracer, TestCaseExecutor
from pynguin.testcase.statement import MethodStatement
from pynguin.utils.generic.genericaccessibleobject import GenericMethod
from tests.fixtures.linecoverage.setter_getter import SetterGetter


@pytest.fixture
def plus_three_test():
    cluster = generate_test_cluster("tests.fixtures.linecoverage.plus")
    transformer = AstToTestCaseTransformer(cluster, False, EmptyConstantProvider())
    transformer.visit(
        ast.parse(
            """def test_case_0():
    int_0 = 3360
    plus_0 = module_0.Plus()
    var_0 = plus_0.plus_three(int_0)
"""
        )
    )
    return transformer.testcases[0]


def test_testsuite_statement_checked_coverage_calculation(plus_three_test):
    module_name = "tests.fixtures.linecoverage.plus"
    test_suite = tsc.TestSuiteChromosome()
    test_suite.add_test_case_chromosome(
        tcc.TestCaseChromosome(test_case=plus_three_test)
    )
    config.configuration.statistics_output.coverage_metrics = [
        config.CoverageMetric.CHECKED,
    ]

    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    with install_import_hook(module_name, tracer):
        module = importlib.import_module(module_name)
        importlib.reload(module)

        executor = TestCaseExecutor(tracer)
        executor.add_observer(StatementSlicingObserver(tracer))

        ff = TestSuiteStatementCheckedCoverageFunction(executor)
        assert ff.compute_coverage(test_suite) == pytest.approx(4 / 8, 0.1, 0.1)


def test_testcase_statement_checked_coverage_calculation(plus_three_test):
    module_name = "tests.fixtures.linecoverage.plus"
    test_case_chromosome = tcc.TestCaseChromosome(test_case=plus_three_test)
    config.configuration.statistics_output.coverage_metrics = [
        config.CoverageMetric.CHECKED,
    ]

    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    with install_import_hook(module_name, tracer):
        module = importlib.import_module(module_name)
        importlib.reload(module)

        executor = TestCaseExecutor(tracer)
        executor.add_observer(StatementSlicingObserver(tracer))

        ff = TestCaseStatementCheckedCoverageFunction(executor)
        assert ff.compute_coverage(test_case_chromosome) == pytest.approx(
            4 / 8, 0.1, 0.1
        )


@pytest.fixture
def setter_test():
    cluster = generate_test_cluster("tests.fixtures.linecoverage.setter_getter")
    transformer = AstToTestCaseTransformer(cluster, False, EmptyConstantProvider())
    transformer.visit(
        ast.parse(
            """def test_case_0():
    setter_getter_0 = module_0.SetterGetter()
    int_0 = 3360
"""
        )
    )
    tc = transformer.testcases[0]

    # we have to manually add a method call without assign,
    # since the AST Parser would ignore this statement
    # without assigning a new variable
    tc.add_statement(
        MethodStatement(
            tc,
            GenericMethod(
                SetterGetter,
                SetterGetter.setter,
                InferredSignature(
                    signature=inspect.signature(SetterGetter.setter),
                    parameters={"new_attribute": int},
                    return_type=None,
                ),
            ),
            tc.statements[0].ret_val,
            {"new_value": tc.statements[1].ret_val},
        )
    )
    return tc


def test_only_void_function(setter_test):
    """Test if implicit return nones are correctly filtered from the sliced
    assignment to a none type for methods with none return type."""
    module_name = "tests.fixtures.linecoverage.setter_getter"
    test_case_chromosome = tcc.TestCaseChromosome(test_case=setter_test)
    config.configuration.statistics_output.coverage_metrics = [
        config.CoverageMetric.CHECKED,
    ]

    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    with install_import_hook(module_name, tracer):
        module = importlib.import_module(module_name)
        importlib.reload(module)

        executor = TestCaseExecutor(tracer)
        executor.add_observer(StatementSlicingObserver(tracer))

        ff = TestCaseStatementCheckedCoverageFunction(executor)
        assert ff.compute_coverage(test_case_chromosome) == pytest.approx(
            3 / 6, 0.1, 0.1
        )


@pytest.fixture
def getter_setter_test():
    cluster = generate_test_cluster("tests.fixtures.linecoverage.setter_getter")
    transformer = AstToTestCaseTransformer(cluster, False, EmptyConstantProvider())
    transformer.visit(
        ast.parse(
            """def test_case_0():
    setter_getter_0 = module_0.SetterGetter()
    int_0 = 3360
    int_1 = setter_getter_0.getter()
"""
        )
    )
    tc = transformer.testcases[0]

    # we have to manually add a method call without assign,
    # since the AST Parser would ignore this statement
    # without assigning a new variable
    tc.add_statement(
        MethodStatement(
            tc,
            GenericMethod(
                SetterGetter,
                SetterGetter.setter,
                InferredSignature(
                    signature=inspect.signature(SetterGetter.setter),
                    parameters={"new_attribute": int},
                    return_type=None,
                ),
            ),
            tc.statements[0].ret_val,
            {"new_value": tc.statements[1].ret_val},
        )
    )
    return tc


def test_getter_before_setter(getter_setter_test):
    """If the getter is before after the setter, the value retrieved by the getter
    is not depending on the new set value. Therefore, the body of the setter should
    npt be included in the slice."""
    module_name = "tests.fixtures.linecoverage.setter_getter"
    test_case_chromosome = tcc.TestCaseChromosome(test_case=getter_setter_test)
    config.configuration.statistics_output.coverage_metrics = [
        config.CoverageMetric.CHECKED,
    ]

    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    with install_import_hook(module_name, tracer):
        module = importlib.import_module(module_name)
        importlib.reload(module)

        executor = TestCaseExecutor(tracer)
        executor.add_observer(StatementSlicingObserver(tracer))

        ff = TestCaseStatementCheckedCoverageFunction(executor)
        assert ff.compute_coverage(test_case_chromosome) == pytest.approx(
            5 / 6, 0.1, 0.1
        )


@pytest.fixture
def setter_getter_test():
    cluster = generate_test_cluster("tests.fixtures.linecoverage.setter_getter")
    transformer = AstToTestCaseTransformer(cluster, False, EmptyConstantProvider())
    transformer.visit(
        ast.parse(
            """def test_case_0():
    setter_getter_0 = module_0.SetterGetter()
    int_0 = 3360
"""
        )
    )
    tc = transformer.testcases[0]

    # we have to manually add a method call without assign,
    # since the AST Parser would ignore this statement
    # without assigning a new variable
    tc.add_statement(
        MethodStatement(
            tc,
            GenericMethod(
                SetterGetter,
                SetterGetter.setter,
                InferredSignature(
                    signature=inspect.signature(SetterGetter.setter),
                    parameters={"new_attribute": int},
                    return_type=None,
                ),
            ),
            tc.statements[0].ret_val,
            {"new_value": tc.statements[1].ret_val},
        )
    )

    tc.add_statement(
        MethodStatement(
            tc,
            GenericMethod(
                SetterGetter,
                SetterGetter.getter,
                InferredSignature(
                    signature=inspect.signature(SetterGetter.getter),
                    parameters={},
                    return_type=int,
                ),
            ),
            tc.statements[0].ret_val,
        )
    )
    return tc


def test_getter_after_setter(setter_getter_test):
    """If the getter is called after the setter, the value retrieved by the getter
    is depending on the new set value. Therefore, all lines of the setter should be included
    in the slice, but the initial setting of the class attribute is not included."""
    module_name = "tests.fixtures.linecoverage.setter_getter"
    test_case_chromosome = tcc.TestCaseChromosome(test_case=setter_getter_test)
    config.configuration.statistics_output.coverage_metrics = [
        config.CoverageMetric.CHECKED,
    ]

    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    with install_import_hook(module_name, tracer):
        module = importlib.import_module(module_name)
        importlib.reload(module)

        executor = TestCaseExecutor(tracer)
        executor.add_observer(StatementSlicingObserver(tracer))

        ff = TestCaseStatementCheckedCoverageFunction(executor)
        assert ff.compute_coverage(test_case_chromosome) == pytest.approx(
            5 / 6, 0.1, 0.1
        )


def test_get_line_id_by_instruction_throws_error():
    instruction_mock = MagicMock(
        code_object_id=0,
        file="foo",
        lineno=1,
    )
    known_data_mock = MagicMock(
        existing_lines={
            0: MagicMock(
                code_object_id=0,
                file="foo",
                lineno=2,
            )
        }
    )

    with pytest.raises(ValueError):
        DynamicSlicer.get_line_id_by_instruction(instruction_mock, known_data_mock)