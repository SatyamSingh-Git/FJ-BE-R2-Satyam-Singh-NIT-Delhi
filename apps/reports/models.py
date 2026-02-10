# Reports app doesn't need models - it generates reports from other models
# This file is intentionally minimal

from django.db import models

# Reports are generated dynamically from Transaction, Budget, and Category data
# No persistent storage needed for reports
