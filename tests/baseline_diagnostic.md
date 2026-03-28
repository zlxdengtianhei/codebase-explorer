# Feature Cone Diagnostic Report

Generated: 2026-03-26T00:12:57.509480+00:00

## Scoring Overview

| Repo                 | Total |    D1 Uniqueness |  D2 Distribution | D3 InfraAccuracy |      D4 Coverage |  D5 DirCoherence |  D6 DepIntegrity | D7 NamingQuality |
|----------------------|-------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|
| celery               |  74.5 |  14.8/15          |   8.4/15          |  10.3/15          |  10.0/10          |  10.7/15          |   5.4/15          |  14.8/15          |
| fastapi              |  77.2 |  14.9/15          |   8.6/15          |  10.8/15          |  10.0/10          |  14.8/15          |   3.2/15          |  15.0/15          |
| flask                |  76.1 |  15.0/15          |   8.1/15          |   9.6/15          |  10.0/10          |  11.7/15          |   7.2/15          |  14.6/15          |
| rich                 |  75.0 |  14.0/15          |   9.8/15          |   2.1/15          |  10.0/10          |   9.8/15          |  15.0/15          |  14.4/15          |
| scrapy               |  77.8 |  14.8/15          |   8.1/15          |  10.4/15          |  10.0/10          |  13.7/15          |   6.0/15          |  14.8/15          |

**Aggregate Mean: 76.1/100**

### celery

```
D1 Uniqueness        ███████████████████░  14.8/15
D2 Distribution      ███████████░░░░░░░░░   8.4/15
D3 InfraAccuracy     █████████████░░░░░░░  10.3/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ██████████████░░░░░░  10.7/15
D6 DepIntegrity      ███████░░░░░░░░░░░░░   5.4/15
D7 NamingQuality     ███████████████████░  14.8/15
```

### fastapi

```
D1 Uniqueness        ███████████████████░  14.9/15
D2 Distribution      ███████████░░░░░░░░░   8.6/15
D3 InfraAccuracy     ██████████████░░░░░░  10.8/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ███████████████████░  14.8/15
D6 DepIntegrity      ████░░░░░░░░░░░░░░░░   3.2/15
D7 NamingQuality     ███████████████████░  15.0/15
```

### flask

```
D1 Uniqueness        ████████████████████  15.0/15
D2 Distribution      ██████████░░░░░░░░░░   8.1/15
D3 InfraAccuracy     ████████████░░░░░░░░   9.6/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ███████████████░░░░░  11.7/15
D6 DepIntegrity      █████████░░░░░░░░░░░   7.2/15
D7 NamingQuality     ███████████████████░  14.6/15
```

### rich

```
D1 Uniqueness        ██████████████████░░  14.0/15
D2 Distribution      █████████████░░░░░░░   9.8/15
D3 InfraAccuracy     ██░░░░░░░░░░░░░░░░░░   2.1/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      █████████████░░░░░░░   9.8/15
D6 DepIntegrity      ████████████████████  15.0/15
D7 NamingQuality     ███████████████████░  14.4/15
```

### scrapy

```
D1 Uniqueness        ███████████████████░  14.8/15
D2 Distribution      ██████████░░░░░░░░░░   8.1/15
D3 InfraAccuracy     █████████████░░░░░░░  10.4/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ██████████████████░░  13.7/15
D6 DepIntegrity      ████████░░░░░░░░░░░░   6.0/15
D7 NamingQuality     ███████████████████░  14.8/15
```

## Weakest Dimensions

1. **D6 DepIntegrity**: avg 7.3/15 (49%)
   - celery: 5.4
   - fastapi: 3.2
   - flask: 7.2
   - rich: 15.0
   - scrapy: 6.0
2. **D2 Distribution**: avg 8.6/15 (57%)
   - celery: 8.4
   - fastapi: 8.6
   - flask: 8.1
   - rich: 9.8
   - scrapy: 8.1
3. **D3 InfraAccuracy**: avg 8.6/15 (58%)
   - celery: 10.3
   - fastapi: 10.8
   - flask: 9.6
   - rich: 2.1
   - scrapy: 10.4

## Actionable Recommendations

- When splitting cones, prefer cuts that don't break strong call/inherit dependency edges.
- Tune shared_threshold and BFS parameters to reduce single-file cones and prevent mega-cones.
- Improve hub detection with out-degree ratio filter to distinguish functional modules from utilities.
