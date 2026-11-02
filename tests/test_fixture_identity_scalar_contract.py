"""Pure scalar contracts, including adversarial admission and evaluation order."""
import pytest

from engines import fixture_identity_read_model as identity


@pytest.mark.parametrize("value", [None, False, True, 0, 17, -17, 0.0, -0.0, 1.25, "", "Málaga", "🦈"])
def test_supported_scalars_return_the_exact_original_object(value):
    assert identity._identity_scalar(value) is value


@pytest.mark.parametrize("unit", ["a", "🦈", "é"])
def test_string_limit_counts_unicode_characters_without_rewriting(unit):
    value = unit * 256
    assert len(value) == 256
    assert identity._identity_scalar(value) is value
    with pytest.raises(identity._IdentityLimit, match="^identity scalar too long$"):
        identity._identity_scalar(value + unit)


def test_combining_unicode_is_neither_normalized_nor_counted_as_graphemes():
    value = "e\u0301" * 128
    assert len(value) == 256
    assert identity._identity_scalar(value) is value
    with pytest.raises(identity._IdentityLimit, match="^identity scalar too long$"):
        identity._identity_scalar(value + "\u0301")
    short = "abc"
    assert identity._identity_scalar(short, limit=3) is short
    with pytest.raises(identity._IdentityLimit, match="^identity scalar too long$"):
        identity._identity_scalar("abcd", limit=3)


@pytest.mark.parametrize("value", [(1 << 850) - 1, -(1 << 849)])
def test_850_bit_integer_is_returned_without_conversion(value):
    assert value.bit_length() == 850
    assert identity._identity_scalar(value) is value


@pytest.mark.parametrize("value", [1 << 850, -(1 << 850)])
def test_851_bit_integer_is_rejected(value):
    assert value.bit_length() == 851
    with pytest.raises(identity._IdentityLimit, match="^identity integer too long$"):
        identity._identity_scalar(value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_builtin_floats_are_rejected(value):
    with pytest.raises(identity._IdentityLimit, match="^nonfinite identity scalar$"):
        identity._identity_scalar(value)


@pytest.mark.parametrize("value", [False, True])
def test_bool_is_a_scalar_but_cannot_be_an_identifier(value):
    assert identity._identity_scalar(value, identifier=False) is value
    with pytest.raises(identity._IdentityLimit, match="^unsupported identity identifier$"):
        identity._identity_scalar(value, identifier=True)


@pytest.mark.parametrize("value", [None, 0, 1, 1.5, "0"])
def test_identifier_flag_does_not_add_other_type_restrictions(value):
    assert identity._identity_scalar(value, identifier=True) is value


class PlainText(str):
    pass


class PlainInt(int):
    pass


class PlainFloat(float):
    pass


@pytest.mark.parametrize("value", [PlainText("x"), PlainText("x" * 257), PlainInt(1), PlainInt(1 << 850), PlainFloat(1.5), PlainFloat("inf")])
def test_ordinary_subclasses_are_rejected_before_value_specific_checks(value):
    with pytest.raises(identity._IdentityLimit, match="^unsupported identity scalar$"):
        identity._identity_scalar(value)


@pytest.mark.parametrize("value", [b"x", bytearray(b"x"), [], {}, (), {"x"}, 1j])
def test_other_builtin_types_remain_unsupported(value):
    with pytest.raises(identity._IdentityLimit, match="^unsupported identity scalar$"):
        identity._identity_scalar(value)


class FlagFailure(RuntimeError):
    pass


@pytest.mark.parametrize("value", [None, False, "x", "x" * 257, 1 << 850, float("inf")])
def test_identifier_truthiness_precedes_supported_value_specific_validation(value):
    calls = []

    class RaisingFlag:
        def __bool__(self):
            calls.append("identifier")
            raise FlagFailure("identifier evaluated first")

    with pytest.raises(FlagFailure, match="^identifier evaluated first$"):
        identity._identity_scalar(value, identifier=RaisingFlag())
    assert calls == ["identifier"]


def test_unsupported_objects_do_not_invoke_value_or_identifier_hooks():
    calls = []

    class Unsupported:
        def __str__(self):
            calls.append("str")
            raise AssertionError("unsupported value was stringified")

        def __bool__(self):
            calls.append("value-bool")
            raise AssertionError("unsupported value was tested for truth")

    class Flag:
        def __bool__(self):
            calls.append("identifier-bool")
            raise AssertionError("identifier preceded scalar type rejection")

    with pytest.raises(identity._IdentityLimit, match="^unsupported identity scalar$"):
        identity._identity_scalar(Unsupported(), identifier=Flag())
    assert calls == []


def _admitted_text(events, *, admit=True, length_failure=False):
    class ScalarMeta(type):
        def __hash__(cls):
            events.append("type-hash")
            return hash(str)

        def __eq__(cls, other):
            events.append("type-eq-str" if other is str else "type-eq-other")
            return admit and other is str

    class AdmittedText(str, metaclass=ScalarMeta):
        def __len__(self):
            events.append("length")
            if length_failure:
                raise FlagFailure("length hook retained")
            return str.__len__(self)

    return AdmittedText


@pytest.mark.parametrize("length", [3, 256, 257])
@pytest.mark.parametrize("identifier", [False, True])
def test_metaclass_admitted_string_preserves_identity_length_and_hook_order(length, identifier):
    events = []
    Text = _admitted_text(events)
    value = Text("x" * length)

    class Flag:
        def __bool__(self):
            events.append("identifier")
            return identifier

    events.clear()
    if length > 256:
        with pytest.raises(identity._IdentityLimit, match="^identity scalar too long$"):
            identity._identity_scalar(value, identifier=Flag())
    else:
        assert identity._identity_scalar(value, identifier=Flag()) is value
    assert events == ["type-hash", "type-eq-str", "identifier", "length"]


def test_metaclass_rejected_string_stops_before_identifier_or_length():
    events = []
    Text = _admitted_text(events, admit=False)

    class Flag:
        def __bool__(self):
            events.append("identifier")
            return True

    with pytest.raises(identity._IdentityLimit, match="^unsupported identity scalar$"):
        identity._identity_scalar(Text("x" * 257), identifier=Flag())
    assert "type-hash" in events and "type-eq-str" in events
    assert "identifier" not in events and "length" not in events


def test_admitted_string_length_exception_still_occurs_after_identifier():
    events = []
    Text = _admitted_text(events, length_failure=True)

    class Flag:
        def __bool__(self):
            events.append("identifier")
            return False

    with pytest.raises(FlagFailure, match="^length hook retained$"):
        identity._identity_scalar(Text("x"), identifier=Flag())
    assert events.index("identifier") < events.index("length")


@pytest.mark.parametrize("failure", ["hash", "equality"])
def test_type_membership_hook_exceptions_precede_identifier(failure):
    events = []

    class RaisingMeta(type):
        def __hash__(cls):
            events.append("hash")
            if failure == "hash":
                raise FlagFailure("type hash failure")
            return hash(str)

        def __eq__(cls, other):
            events.append("equality")
            raise FlagFailure("type equality failure")

    class Value(str, metaclass=RaisingMeta):
        pass

    class Flag:
        def __bool__(self):
            events.append("identifier")
            raise AssertionError("membership failure must occur first")

    with pytest.raises(FlagFailure, match="^type " + failure + " failure$"):
        identity._identity_scalar(Value("x"), identifier=Flag())
    assert events == (["hash"] if failure == "hash" else ["hash", "equality"])
