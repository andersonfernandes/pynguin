#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2023 Pynguin Contributors
#
#  SPDX-License-Identifier: MIT
#
"""Defines an abstract test case visitor."""

from abc import ABC
from abc import abstractmethod


# pylint: disable=too-few-public-methods
class TestCaseVisitor(ABC):
    """An abstract test case visitor."""

    @abstractmethod
    def visit_default_test_case(self, test_case) -> None:
        """Visit a default test case.

        Args:
            test_case: The test case
        """
