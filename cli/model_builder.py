# cli/model_builder.py

"""
Translate loaded YAML policy definitions into SMT-LIB2 code
reflecting the formal model from Section IV.
"""
from textwrap import dedent

def build_smt_for_registry(policy):
    """
    SMT for the 'registry' case:
      - assert registry = test_registry
      - (if prefix_bad) assert prefix-match
      - assert (not allowed) to find violations
    """
    allowed = policy["allowed_registries"]
    test_reg = policy["test_registry"]
    prefix_bad = policy.get("prefix_bad", False)

    allowed_checks = " ".join(f'(= registry "{r}")' for r in allowed)
    prefix_assert = f'(assert (str.prefixof "{allowed[0]}" registry))' if prefix_bad else ""

    smt = dedent(f"""
        ; SMT model for registry case: {policy.get('name')}
        (set-logic QF_S)
        (declare-fun registry () String)

        ; Constrain to our test_registry
        (assert (= registry "{test_reg}"))

        (define-fun allowed () Bool
          (or {allowed_checks}))

        {prefix_assert}
        ; Security invariant: only exact matches allowed
        (assert (not allowed))

        (check-sat)
        (get-model)
    """).strip()

    return smt


def build_smt_for_wildcard(policy):
    """
    Given a dict with keys:
      - subject_is_admin: bool
      - resource_kind: string
      - action: string
      - wildcard_present: bool
    produce SMT-LIB code that asserts:
      kind == resource_kind
      action == action
      isAdmin == subject_is_admin
      hasWildcard == wildcard_present
      then asserts (and (not isAdmin) hasWildcard) to test violation.
    """
    kind = policy["resource_kind"]
    action = policy["action"]
    is_admin = "true" if policy["subject_is_admin"] else "false"
    has_wild = "true" if policy["wildcard_present"] else "false"

    smt = dedent(f"""
        ; SMT model for wildcard role-binding case: {policy.get('name')}
        (set-logic QF_S)
        (declare-fun kind () String)
        (declare-fun action () String)
        (declare-fun isAdmin () Bool)
        (declare-fun hasWildcard () Bool)

        (assert (= kind "{kind}"))
        (assert (= action "{action}"))
        (assert (= isAdmin {is_admin}))
        (assert (= hasWildcard {has_wild}))

        ; Invariant: non-admin + wildcard => forbidden
        (assert (and (not isAdmin) hasWildcard))

        (check-sat)
        (get-model)
    """).strip()
    return smt


def build_smt_for_tenant(policy):
    """
    Given a dict with keys:
      - subject_tenant: string
      - resource_tenant: string
    produce SMT-LIB to assert they differ, i.e. violation.
    """
    subj = policy["subject_tenant"]
    res  = policy["resource_tenant"]

    smt = dedent(f"""
        ; SMT model for tenant isolation case: {policy.get('name')}
        (set-logic QF_S)
        (declare-fun subTenant () String)
        (declare-fun resTenant () String)

        (assert (= subTenant "{subj}"))
        (assert (= resTenant "{res}"))

        ; Invariant: cross-tenant must be forbidden
        (assert (not (= subTenant resTenant)))

        (check-sat)
        (get-model)
    """).strip()
    return smt
