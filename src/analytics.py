import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Define analytics file path
ANALYTICS_DIR = Path.home() / ".cache" / "referencing"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
ANALYTICS_FILE = ANALYTICS_DIR / "analytics_events.jsonl"

logger = logging.getLogger(__name__)

class AnalyticsLogger:
    """Simple file-based logger for analytics events."""
    
    @staticmethod
    def log_event(event_type: str, data: Dict[str, Any], project_id: str = None):
        """Log an event to the analytics file (JSONL format)."""
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": event_type,
            "project_id": project_id,
            "data": data
        }
        try:
            with open(ANALYTICS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to log analytics event: {e}")

    @staticmethod
    def log_compliance_report(result: Any, project_id: str = None):
        """
        Log summary stats from a compliance report result dictionary.
        """
        try:
            # Extract the actual report object from the dictionary
            report = result.get('report') if isinstance(result, dict) else result
            if not report:
                logger.error("No report found in compliance result")
                return

            stats = report.counts
            
            # Count rule violations for the 'Top Offender' chart
            violation_counts = {}
            for ref in report.references:
                for v in ref.violations:
                    rule = v.rule_id
                    violation_counts[rule] = violation_counts.get(rule, 0) + 1

            data = {
                "overall_score": report.overall_compliance_score,
                "total_references": len(report.references),
                "error_count": stats.errors,
                "warning_count": stats.warnings,
                "info_count": stats.suggestions,
                "violation_distribution": violation_counts
            }
            AnalyticsLogger.log_event("compliance_report_generated", data, project_id=project_id)
        except Exception as e:
            logger.error(f"Failed to extract compliance stats: {e}")

    @staticmethod
    def log_edit_event(ref_id: str, changes: Dict[str, Any], project_id: str = None):
        """Log manual edits."""
        AnalyticsLogger.log_event("reference_edited", {
            "reference_id": ref_id,
            "changes": changes
        }, project_id=project_id)

    @staticmethod
    def get_all_events(project_id: str = None):
        """Read all events from the log file, optionally filtered by project_id."""
        events = []
        if not ANALYTICS_FILE.exists():
            return events
            
        try:
            with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        event = json.loads(line)
                        # Filter by project_id if provided. 
                        # Legacy events with no project_id are excluded when filtering for a specific project.
                        if project_id and event.get("project_id") != project_id:
                            continue
                        events.append(event)
        except Exception as e:
            logger.error(f"Failed to read analytics events: {e}")
        return events

    @staticmethod
    def get_summary_stats(project_id: str = None):
        """Aggregate stats for the dashboard, optionally filtered by project_id."""
        events = AnalyticsLogger.get_all_events(project_id=project_id)
        
        compliance_events = [e for e in events if e["event_type"] == "compliance_report_generated"]
        edit_events = [e for e in events if e["event_type"] == "reference_edited"]
        
        # Trend data (Timestamp, Score)
        trend_data = []
        violation_totals = {}
        
        total_score = 0
        for e in compliance_events:
            d = e["data"]
            score = d.get("overall_score", 0)
            total_score += score
            trend_data.append({
                "t": e["timestamp"],
                "y": round(score, 1)
            })
            
            # Aggregate violations
            dist = d.get("violation_distribution", {})
            for rule, count in dist.items():
                violation_totals[rule] = violation_totals.get(rule, 0) + count

        avg_score = (total_score / len(compliance_events)) if compliance_events else 0
        
        # Sort violations for 'Top Offenders'
        top_offenders = sorted(violation_totals.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_reports": len(compliance_events),
            "total_edits": len(edit_events),
            "average_score": round(avg_score, 1),
            "trend": trend_data,
            "top_offenders": top_offenders,
            "violation_totals": violation_totals
        }

    @staticmethod
    def get_proactive_suggestions(project_id: str = None):
        """Analyze edit patterns to suggest improvements, optionally filtered by project_id."""
        events = AnalyticsLogger.get_all_events(project_id=project_id)
        edit_events = [e for e in events if e["event_type"] == "reference_edited"]
        
        suggestions = []
        
        # Pattern 1: Title Case Correction
        case_corrections = 0
        for e in edit_events:
            old_title = e["data"]["changes"]["old"].get("title", "")
            new_title = e["data"]["changes"]["new"].get("title", "")
            if old_title.isupper() and not new_title.isupper():
                case_corrections += 1
        
        if case_corrections >= 3:
            suggestions.append({
                "title": "Title Case Pattern Detected",
                "message": f"You've manually corrected Title Case {case_corrections} times. Consider using a 'Sentence Case' import filter.",
                "type": "info"
            })

        # Pattern 2: Missing Publisher adds
        publisher_adds = 0
        for e in edit_events:
            old_pub = e["data"]["changes"]["old"].get("publisher", "")
            new_pub = e["data"]["changes"]["new"].get("publisher", "")
            if not old_pub and new_pub:
                publisher_adds += 1
        
        if publisher_adds >= 2:
            suggestions.append({
                "title": "Frequent Publisher Corrections",
                "message": "You are often adding missing Publishers. We recommend checking if your primary data source (e.g. CrossRef) provides this metadata.",
                "type": "warning"
            })
            
        return suggestions

