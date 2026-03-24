from csvmetrics.importer import ImportErrorDetail, MetricRecord, import_metrics


def test_imports_valid_rows_in_order():
    result = import_metrics(
        "metric,value,unit\n"
        "requests,12,count\n"
        "latency,18.5,ms\n"
    )

    assert result.records == [
        MetricRecord(metric="requests", value=12.0, unit="count"),
        MetricRecord(metric="latency", value=18.5, unit="ms"),
    ]
    assert result.errors == []


def test_invalid_numeric_rows_are_reported():
    result = import_metrics(
        "metric,value,unit\n"
        "requests,12,count\n"
        "latency,n/a,ms\n"
    )

    assert result.records == [
        MetricRecord(metric="requests", value=12.0, unit="count"),
    ]
    assert result.errors == [
        ImportErrorDetail(
            line=3,
            code="invalid-number",
            message="invalid numeric value 'n/a' for metric 'latency'",
        )
    ]
