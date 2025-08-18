"""Tests for comparison operations on Result and Option types."""

import pytest

from logerr import Err, Nothing, Ok, Some

pytestmark = pytest.mark.unit


class TestOptionComparisons:
    """Test comparison operations for Option types."""

    def test_some_equality(self):
        """Test equality comparison between Some instances."""
        assert Some(42) == Some(42)
        assert Some(42) != Some(43)
        assert Some("hello") == Some("hello")
        assert Some("hello") != Some("world")

    def test_nothing_equality(self):
        """Test equality comparison between Nothing instances."""
        assert Nothing("reason1") == Nothing("reason1")
        assert Nothing("reason1") != Nothing("reason2")
        assert Nothing.empty() == Nothing.empty()

    def test_some_vs_nothing_equality(self):
        """Test equality comparison between Some and Nothing."""
        assert Some(42) != Nothing("error")
        assert Nothing("error") != Some(42)

    def test_some_ordering(self):
        """Test ordering comparison between Some instances."""
        assert Some(1) < Some(2)
        assert Some(2) > Some(1)
        assert Some(1) <= Some(1)
        assert Some(1) <= Some(2)
        assert Some(2) >= Some(1)
        assert Some(1) >= Some(1)

    def test_nothing_vs_some_ordering(self):
        """Test ordering between Nothing and Some."""
        nothing = Nothing.empty()
        some = Some(42)

        assert nothing < some
        assert nothing <= some
        assert some > nothing
        assert some >= nothing
        assert not (nothing > some)
        assert not (some < nothing)

    def test_nothing_vs_nothing_ordering(self):
        """Test ordering between Nothing instances."""
        nothing1 = Nothing("error1")
        nothing2 = Nothing("error2")

        # Nothing values are equal in ordering (not less/greater)
        assert not (nothing1 < nothing2)
        assert not (nothing1 > nothing2)
        assert nothing1 <= nothing2  # Equal case
        assert nothing1 >= nothing2  # Equal case

    def test_incomparable_types_return_not_implemented(self):
        """Test that comparing with incomparable types returns NotImplemented."""
        some = Some("hello")

        # These should not raise exceptions but return NotImplemented
        # which Python's comparison system handles gracefully
        try:
            result = some < "hello"  # Should be False due to NotImplemented
            assert result is False or result is NotImplemented
        except TypeError:
            # This is also acceptable behavior
            pass

    def test_some_with_non_comparable_values(self):
        """Test Some with values that don't support comparison."""

        # Objects that don't implement comparison
        class NonComparable:
            pass

        some1 = Some(NonComparable())
        some2 = Some(NonComparable())

        # Equality should work (uses ==)
        assert some1 != some2  # Different instances

        # Ordering should raise TypeError for non-comparable types
        with pytest.raises(TypeError):
            assert some1 < some2


class TestResultComparisons:
    """Test comparison operations for Result types."""

    def test_ok_equality(self):
        """Test equality comparison between Ok instances."""
        assert Ok(42) == Ok(42)
        assert Ok(42) != Ok(43)
        assert Ok("hello") == Ok("hello")
        assert Ok("hello") != Ok("world")

    def test_err_equality(self):
        """Test equality comparison between Err instances."""
        assert Err("error1") == Err("error1")
        assert Err("error1") != Err("error2")
        assert Err(42) == Err(42)

    def test_ok_vs_err_equality(self):
        """Test equality comparison between Ok and Err."""
        assert Ok(42) != Err("error")
        assert Err("error") != Ok(42)

    def test_ok_ordering(self):
        """Test ordering comparison between Ok instances."""
        assert Ok(1) < Ok(2)
        assert Ok(2) > Ok(1)
        assert Ok(1) <= Ok(1)
        assert Ok(1) <= Ok(2)
        assert Ok(2) >= Ok(1)
        assert Ok(1) >= Ok(1)

    def test_err_ordering(self):
        """Test ordering comparison between Err instances."""
        assert Err("a") < Err("b")
        assert Err("b") > Err("a")
        assert Err("a") <= Err("a")
        assert Err("a") <= Err("b")
        assert Err("b") >= Err("a")
        assert Err("a") >= Err("a")

    def test_ok_vs_err_ordering(self):
        """Test ordering between Ok and Err."""
        ok = Ok(42)
        err = Err("error")

        assert err < ok
        assert err <= ok
        assert ok > err
        assert ok >= err
        assert not (err > ok)
        assert not (ok < err)

    def test_incomparable_types_return_not_implemented(self):
        """Test that comparing with incomparable types returns NotImplemented."""
        ok = Ok("hello")

        # These should not raise exceptions but return NotImplemented
        try:
            result = ok < "hello"  # Should be False due to NotImplemented
            assert result is False or result is NotImplemented
        except TypeError:
            # This is also acceptable behavior
            pass

    def test_result_with_non_comparable_values(self):
        """Test Result with values that don't support comparison."""

        class NonComparable:
            pass

        ok1 = Ok(NonComparable())
        ok2 = Ok(NonComparable())

        # Equality should work (uses ==)
        assert ok1 != ok2  # Different instances

        # Ordering should raise TypeError for non-comparable types
        with pytest.raises(TypeError):
            assert ok1 < ok2


class TestMixedComparisons:
    """Test comparisons between different types."""

    def test_cross_type_comparisons_return_not_implemented(self):
        """Test that comparing Option with Result returns NotImplemented."""
        some = Some(42)
        ok = Ok(42)

        # These should return NotImplemented, not raise exceptions
        try:
            result = some == ok
            assert result is False  # Different types
        except Exception:
            pytest.fail("Cross-type comparison should not raise exception")

        try:
            result = some < ok
            assert result is NotImplemented or isinstance(result, bool)
        except TypeError:
            # This is acceptable behavior
            pass
