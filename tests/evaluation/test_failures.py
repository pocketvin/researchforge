from researchforge.evaluation.failures import classify_failure, failure_record


def test_failure_taxonomy_maps_known_runtime_failures() -> None:
    manifest = {
        "run_id": "run_parser",
        "failure": {
            "code": "DISCLOSURE_PARSE_FAILED",
            "stage": "parsing",
            "message": "verified PDF could not be parsed",
            "retryable": False,
        },
    }
    assert classify_failure(manifest) == "PARSER_FAILURE"
    record = failure_record(manifest)
    assert record is not None
    assert record["failure_class"] == "PARSER_FAILURE"
    assert record["regression_case_recommended"] is True


def test_failure_taxonomy_does_not_invent_failure_for_success() -> None:
    assert classify_failure({"run_id": "run_ok", "failure": None}) is None
    assert failure_record({"run_id": "run_ok", "failure": None}) is None
