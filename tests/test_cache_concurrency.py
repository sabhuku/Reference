
import unittest
import threading
import time
from unittest.mock import patch, MagicMock

# Import both the module that has the singleton logic and the class 
import src.referencing.referencing as ref_module
from src.reference_manager import ReferenceManager

# We need to test two things:
# 1. Thread-safe singleton creation via _get_manager
# 2. Thread-safe lazy cache loading via ReferenceManager.cache

class TestCacheConcurrency(unittest.TestCase):
    
    def setUp(self):
        # Reset singleton for fresh test
        ref_module._manager = None
        
    def test_singleton_concurrency(self):
        """Verify _get_manager creates exactly one instance under load."""
        instances = []
        errors = []
        
        def get_instance():
            try:
                inst = ref_module._get_manager()
                instances.append(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_instance) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertTrue(len(instances) > 0)
        
        # Verify all instances are identical
        first = instances[0]
        for inst in instances[1:]:
            self.assertIs(inst, first, "Singleton violation: multiple instances created")

    def test_lazy_cache_loading_concurrency(self):
        """Verify cache loaded exactly once under concurrent access."""
        mgr = ReferenceManager()
        # Mock _load_cache to count calls
        mgr._load_cache = MagicMock(return_value={"test": 1})
        # Reset _cache to None just in case (though init does it)
        mgr._cache = None 
        
        results = []
        
        def access_cache():
            # Artificial delay inside access logic? 
            # We can't easily delay inside the property without patching lock,
            # but usually the race checks 'if self._cache is None'
            time.sleep(0.001) # Jitter
            results.append(mgr.cache)

        threads = [threading.Thread(target=access_cache) for _ in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        # Verify load called once
        mgr._load_cache.assert_called_once()
        self.assertEqual(len(results), 50)
        self.assertEqual(results[0], {"test": 1})

if __name__ == "__main__":
    unittest.main()
