"""NLG diagnostic reporting package for the EV Battery Health Prediction System.

Facts-first pipeline (see TRD section 5):

    validation      -> validate & normalize raw request/prediction data
    fact_extractor  -> build a canonical, typed DiagnosticFacts object
    diagnostic_rules-> deterministic rule engine producing Finding objects
    report_planner  -> select & order findings / sections (content planning)
    sentence_realizer-> render plain-English sentences (lexicalization/aggregation)
    report_generator-> orchestrate the above into a schema-shaped report
    report_validator-> ground every number & reject unsafe/unsupported claims

The package depends only on the Python standard library so it can be imported
and tested without Flask, TensorFlow or scikit-learn installed.
"""

from .config import GENERATOR_VERSION, RULES_VERSION, SCHEMA_VERSION

__all__ = ["GENERATOR_VERSION", "RULES_VERSION", "SCHEMA_VERSION"]
