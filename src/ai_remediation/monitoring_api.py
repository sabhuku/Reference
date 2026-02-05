"""
Monitoring Dashboard API - Week 4 Implementation

Flask API endpoints for monitoring dashboard.
Returns JSON for metrics, feature flags, and system health.
"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from src.ai_remediation.metrics import get_metrics_collector
from src.ai_remediation.feature_flags import FeatureFlagService
from src.ai_remediation.audit_logger import AuditLogger


# Create blueprint
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')


@monitoring_bp.route('/health', methods=['GET'])
def get_health():
    """
    Get system health status.
    
    Returns:
        {
            'status': 'healthy' | 'degraded' | 'critical',
            'timestamp': '2026-02-02T19:30:00Z',
            'checks': {
                'database': 'ok',
                'audit_chain': 'ok',
                'ai_metrics': 'ok'
            }
        }
    """
    from ui.database import db
    
    checks = {}
    overall_status = 'healthy'
    
    # Check 1: Database connectivity
    try:
        db.session.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        overall_status = 'critical'
    
    # Check 2: Audit log chain integrity
    try:
        logger = AuditLogger()
        is_valid, message = logger.verify_chain(limit=100)
        checks['audit_chain'] = 'ok' if is_valid else f'error: {message}'
        if not is_valid:
            overall_status = 'critical'
    except Exception as e:
        checks['audit_chain'] = f'error: {str(e)}'
        overall_status = 'critical'
    
    # Check 3: AI metrics health
    try:
        collector = get_metrics_collector()
        ai_metrics = collector.get_ai_metrics(hours=1)
        checks['ai_metrics'] = ai_metrics['health']
        
        if ai_metrics['health'] == 'critical':
            overall_status = 'critical'
        elif ai_metrics['health'] == 'degraded' and overall_status != 'critical':
            overall_status = 'degraded'
    except Exception as e:
        checks['ai_metrics'] = f'error: {str(e)}'
    
    return jsonify({
        'status': overall_status,
        'timestamp': datetime.utcnow().isoformat(),
        'checks': checks
    })


@monitoring_bp.route('/metrics', methods=['GET'])
def get_metrics():
    """
    Get AI metrics for time window.
    
    Query params:
        hours: Number of hours to look back (default: 24)
    
    Returns:
        {
            'time_window_hours': 24,
            'suggestions': {...},
            'rates': {...},
            'health': 'healthy'
        }
    """
    hours = int(request.args.get('hours', 24))
    
    collector = get_metrics_collector()
    metrics = collector.get_ai_metrics(hours=hours)
    
    return jsonify(metrics)


@monitoring_bp.route('/metrics/detailed', methods=['GET'])
def get_detailed_metrics():
    """
    Get detailed metrics breakdown.
    
    Query params:
        start: Start time (ISO format)
        end: End time (ISO format)
    
    Returns:
        Detailed metrics with hourly breakdown
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    
    if start_str:
        start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
    else:
        start_time = datetime.utcnow() - timedelta(hours=24)
    
    if end_str:
        end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    else:
        end_time = datetime.utcnow()
    
    collector = get_metrics_collector()
    metrics = collector.get_metrics(start_time, end_time)
    
    return jsonify(metrics)


@monitoring_bp.route('/flags', methods=['GET'])
def get_feature_flags():
    """
    Get all feature flags status.
    
    Returns:
        {
            'flags': [
                {
                    'flag_name': 'ai_suggestions',
                    'enabled': False,
                    'rollout_percentage': 0.0,
                    ...
                }
            ]
        }
    """
    from src.ai_remediation.models import FeatureFlag
    
    flags = FeatureFlag.query.all()
    service = FeatureFlagService()
    
    flags_data = []
    for flag in flags:
        status = service.get_flag_status(flag.flag_name)
        if status:
            flags_data.append(status)
    
    return jsonify({'flags': flags_data})


@monitoring_bp.route('/flags/<flag_name>', methods=['GET'])
def get_feature_flag(flag_name: str):
    """
    Get specific feature flag status.
    
    Returns:
        {
            'flag_name': 'ai_suggestions',
            'enabled': False,
            'rollout_percentage': 0.0,
            'user_overrides': {...}
        }
    """
    service = FeatureFlagService()
    status = service.get_flag_status(flag_name)
    
    if not status:
        return jsonify({'error': 'Flag not found'}), 404
    
    return jsonify(status)


@monitoring_bp.route('/flags/<flag_name>/enable', methods=['POST'])
def enable_feature_flag(flag_name: str):
    """
    Enable a feature flag.
    
    Body:
        {
            'rollout_percentage': 0.05,  # 5%
            'reason': 'Starting beta rollout'
        }
    
    Returns:
        {'success': True, 'message': '...'}
    """
    data = request.get_json()
    rollout_percentage = data.get('rollout_percentage', 1.0)
    reason = data.get('reason', 'manual_enable')
    
    service = FeatureFlagService()
    service.enable_flag(flag_name, rollout_percentage, reason)
    
    return jsonify({
        'success': True,
        'message': f"Flag '{flag_name}' enabled at {rollout_percentage*100}%"
    })


@monitoring_bp.route('/flags/<flag_name>/disable', methods=['POST'])
def disable_feature_flag(flag_name: str):
    """
    Disable a feature flag (kill-switch).
    
    Body:
        {
            'reason': 'High error rate detected'
        }
    
    Returns:
        {'success': True, 'message': '...'}
    """
    data = request.get_json()
    reason = data.get('reason', 'manual_disable')
    
    service = FeatureFlagService()
    service.disable_flag(flag_name, reason)
    
    return jsonify({
        'success': True,
        'message': f"Flag '{flag_name}' disabled (kill-switch activated)"
    })


@monitoring_bp.route('/audit/recent', methods=['GET'])
def get_recent_audit_events():
    """
    Get recent audit log events.
    
    Query params:
        limit: Number of events (default: 100)
        event_type: Filter by event type
    
    Returns:
        {
            'events': [...]
        }
    """
    limit = int(request.args.get('limit', 100))
    event_type = request.args.get('event_type')
    
    logger = AuditLogger()
    events = logger.get_events(event_type=event_type, limit=limit)
    
    events_data = [
        {
            'id': e.id,
            'timestamp': e.timestamp.isoformat(),
            'event_type': e.event_type,
            'user_id': e.user_id,
            'reference_id': e.reference_id,
            'suggestion_id': e.suggestion_id,
            'details': e.details
        }
        for e in events
    ]
    
    return jsonify({'events': events_data})


@monitoring_bp.route('/audit/verify', methods=['GET'])
def verify_audit_chain():
    """
    Verify audit log chain integrity.
    
    Query params:
        limit: Number of events to verify (default: 1000)
    
    Returns:
        {
            'valid': True,
            'message': 'Chain verified (1000 events)',
            'timestamp': '...'
        }
    """
    limit = int(request.args.get('limit', 1000))
    
    logger = AuditLogger()
    is_valid, message = logger.verify_chain(limit=limit)
    
    return jsonify({
        'valid': is_valid,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    })


@monitoring_bp.route('/alerts', methods=['GET'])
def get_alerts():
    """
    Get active alerts based on metrics.
    
    Returns:
        {
            'alerts': [
                {
                    'severity': 'critical',
                    'message': 'Acceptance rate below 20%',
                    'metric': 'acceptance_rate',
                    'value': 0.15
                }
            ]
        }
    """
    collector = get_metrics_collector()
    metrics = collector.get_ai_metrics(hours=1)
    
    alerts = []
    
    # Alert 1: Low acceptance rate
    if metrics['rates']['acceptance_rate'] < 0.20:
        alerts.append({
            'severity': 'critical',
            'message': 'Acceptance rate below 20%',
            'metric': 'acceptance_rate',
            'value': metrics['rates']['acceptance_rate'],
            'threshold': 0.20
        })
    elif metrics['rates']['acceptance_rate'] < 0.40:
        alerts.append({
            'severity': 'warning',
            'message': 'Acceptance rate below 40%',
            'metric': 'acceptance_rate',
            'value': metrics['rates']['acceptance_rate'],
            'threshold': 0.40
        })
    
    # Alert 2: High validation failure rate
    if metrics['rates']['validation_failure_rate'] > 0.30:
        alerts.append({
            'severity': 'critical',
            'message': 'Validation failure rate above 30%',
            'metric': 'validation_failure_rate',
            'value': metrics['rates']['validation_failure_rate'],
            'threshold': 0.30
        })
    elif metrics['rates']['validation_failure_rate'] > 0.15:
        alerts.append({
            'severity': 'warning',
            'message': 'Validation failure rate above 15%',
            'metric': 'validation_failure_rate',
            'value': metrics['rates']['validation_failure_rate'],
            'threshold': 0.15
        })
    
    return jsonify({
        'alerts': alerts,
        'timestamp': datetime.utcnow().isoformat()
    })
