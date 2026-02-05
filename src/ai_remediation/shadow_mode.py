"""
Shadow Mode Batch Runner

Runs AI suggestion generation in shadow mode (NO user-facing changes).
Processes batches of references to collect metrics and validate the system.
"""
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from src.ai_remediation.suggestion_orchestrator import SuggestionOrchestrator
from src.ai_remediation.gpt5_service import GPT5Service
from src.ai_remediation.metrics import AIMetricsCollector
from ui.database import db, Reference
from ui.app import app

logger = logging.getLogger(__name__)


class ShadowModeRunner:
    """
    Shadow mode batch runner for AI suggestion testing.
    
    CRITICAL: This is SHADOW MODE ONLY - suggestions are NOT applied to references!
    """
    
    def __init__(
        self,
        orchestrator: Optional[SuggestionOrchestrator] = None,
        batch_size: int = 10
    ):
        """
        Initialize shadow mode runner.
        
        Args:
            orchestrator: Suggestion orchestrator (creates default if None)
            batch_size: Number of references to process at once
        """
        self.batch_size = batch_size
        
        if orchestrator is None:
            # Import here to avoid circular dependencies
            from src.ai_remediation.suggestion_orchestrator import SuggestionOrchestrator
            from ui.database import db
            self.orchestrator = SuggestionOrchestrator(db_session=db.session)
        else:
            self.orchestrator = orchestrator
        
        logger.info(f"ShadowModeRunner initialized (batch_size={batch_size})")
    
    def get_candidate_references(
        self,
        limit: Optional[int] = None,
        bibliography_id: Optional[int] = None
    ) -> List[Reference]:
        """
        Get references suitable for shadow mode testing.
        
        Args:
            limit: Maximum number of references to return
            bibliography_id: Filter by bibliography ID
        
        Returns:
            List of Reference objects
        """
        query = Reference.query
        
        if bibliography_id:
            query = query.filter_by(bibliography_id=bibliography_id)
        
        # Order by ID for deterministic results
        query = query.order_by(Reference.id)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def run_batch(
        self,
        reference_ids: Optional[List[int]] = None,
        limit: int = 100,
        user_id: int = 1,
        tier: str = "tier_1",
        bibliography_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run shadow mode batch processing.
        
        Args:
            reference_ids: Specific reference IDs to process (optional)
            limit: Maximum number of references to process
            user_id: User ID for logging
            tier: Remediation tier (tier_0, tier_1, tier_2)
            bibliography_id: Filter by bibliography ID
        
        Returns:
            Summary of batch results
        """
        start_time = datetime.utcnow()
        
        # Get references to process
        if reference_ids:
            references = [Reference.query.get(rid) for rid in reference_ids]
            references = [r for r in references if r is not None]
        else:
            references = self.get_candidate_references(
                limit=limit,
                bibliography_id=bibliography_id
            )
        
        total_refs = len(references)
        
        logger.info(
            f"Starting shadow mode batch: {total_refs} references, "
            f"tier={tier}, user_id={user_id}"
        )
        
        
        results = {
            'total': total_refs,
            'successful': 0,
            'failed': 0,
            'validation_passed': 0,
            'validation_failed': 0,
            'suggestions': [],
            'errors': [],
            'start_time': start_time.isoformat(),
            'tier': tier,
            'user_id': user_id
        }
        
        # Process in batches
        for i in range(0, total_refs, self.batch_size):
            batch = references[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_refs + self.batch_size - 1) // self.batch_size
            
            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} references)"
            )
            
            for ref in batch:
                try:
                    suggestion = self.orchestrator.generate_and_validate(
                        reference_id=ref.id,
                        user_id=user_id,
                        tier=tier
                    )
                    
                    if suggestion:
                        results['successful'] += 1
                        results['suggestions'].append({
                            'suggestion_id': suggestion['suggestion_id'],
                            'reference_id': suggestion['reference_id'],
                            'validation_passed': suggestion['validation_passed'],
                            'confidence': suggestion['overall_confidence'],
                            'num_patches': len(suggestion['patches'])
                        })
                        
                        if suggestion['validation_passed']:
                            results['validation_passed'] += 1
                        else:
                            results['validation_failed'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'reference_id': ref.id,
                            'error': 'Suggestion generation returned None'
                        })
                
                except Exception as e:
                    logger.error(
                        f"Error processing reference {ref.id}: {e}",
                        exc_info=True
                    )
                    results['failed'] += 1
                    results['errors'].append({
                        'reference_id': ref.id,
                        'error': str(e)
                    })
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration
        results['avg_time_per_reference'] = duration / total_refs if total_refs > 0 else 0
        
        # Calculate statistics
        if results['successful'] > 0:
            results['validation_pass_rate'] = (
                results['validation_passed'] / results['successful']
            )
            results['avg_confidence'] = (
                sum(s['confidence'] for s in results['suggestions']) / 
                results['successful']
            )
            results['avg_patches_per_suggestion'] = (
                sum(s['num_patches'] for s in results['suggestions']) / 
                results['successful']
            )
        else:
            results['validation_pass_rate'] = 0.0
            results['avg_confidence'] = 0.0
            results['avg_patches_per_suggestion'] = 0.0
        
        logger.info(
            f"Shadow mode batch complete: "
            f"{results['successful']}/{results['total']} successful, "
            f"{results['validation_passed']} passed validation, "
            f"avg_confidence={results['avg_confidence']:.2f}, "
            f"duration={duration:.1f}s"
        )
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_file: str):
        """
        Save batch results to JSON file.
        
        Args:
            results: Batch results dictionary
            output_file: Output file path
        """
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")


def main():
    """CLI entry point for shadow mode runner."""
    parser = argparse.ArgumentParser(
        description='Run AI suggestions in shadow mode (NO user-facing changes)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum number of references to process (default: 100)'
    )
    parser.add_argument(
        '--tier',
        choices=['tier_0', 'tier_1', 'tier_2'],
        default='tier_1',
        help='Remediation tier (default: tier_1)'
    )
    parser.add_argument(
        '--bibliography-id',
        type=int,
        help='Filter by bibliography ID'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for processing (default: 10)'
    )
    parser.add_argument(
        '--output',
        default='shadow_mode_results.json',
        help='Output file for results (default: shadow_mode_results.json)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: process only 5 references'
    )
    
    args = parser.parse_args()
    
    # Test mode overrides
    if args.test:
        args.limit = 5
        logger.info("TEST MODE: Processing only 5 references")
    
    # Run in Flask app context
    with app.app_context():
        runner = ShadowModeRunner(batch_size=args.batch_size)
        
        results = runner.run_batch(
            limit=args.limit,
            tier=args.tier,
            bibliography_id=args.bibliography_id
        )
        
        # Save results
        runner.save_results(results, args.output)
        
        # Print summary
        print("\n" + "="*60)
        print("SHADOW MODE BATCH RESULTS")
        print("="*60)
        print(f"Total references:        {results['total']}")
        print(f"Successful:              {results['successful']}")
        print(f"Failed:                  {results['failed']}")
        print(f"Validation passed:       {results['validation_passed']}")
        print(f"Validation failed:       {results['validation_failed']}")
        print(f"Validation pass rate:    {results['validation_pass_rate']:.1%}")
        print(f"Avg confidence:          {results['avg_confidence']:.2f}")
        print(f"Avg patches/suggestion:  {results['avg_patches_per_suggestion']:.1f}")
        print(f"Duration:                {results['duration_seconds']:.1f}s")
        print(f"Avg time/reference:      {results['avg_time_per_reference']:.2f}s")
        print("="*60)
        print(f"\nResults saved to: {args.output}")
        print("\nREMINDER: This is SHADOW MODE - NO changes applied to references!")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
