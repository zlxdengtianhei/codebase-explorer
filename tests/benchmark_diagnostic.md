# Feature Cone Diagnostic Report

Generated: 2026-03-26T00:21:06.229366+00:00

## Scoring Overview

| Repo                 | Total |    D1 Uniqueness |  D2 Distribution | D3 InfraAccuracy |      D4 Coverage |  D5 DirCoherence |  D6 DepIntegrity | D7 NamingQuality |
|----------------------|-------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|
| celery               |  75.2 |  15.0/15          |   8.3/15          |  10.6/15          |  10.0/10          |  11.4/15          |   5.1/15          |  14.8/15          |
| fastapi              |  81.2 |  15.0/15          |   8.5/15          |  10.8/15          |  10.0/10          |  14.8/15          |   7.1/15          |  15.0/15          |
| flask                |  76.1 |  15.0/15          |   8.1/15          |   9.6/15          |  10.0/10          |  11.7/15          |   7.2/15          |  14.6/15          |
| rich                 |  78.5 |  15.0/15          |  10.5/15          |   4.3/15          |  10.0/10          |   9.4/15          |  15.0/15          |  14.3/15          |
| scrapy               |  78.6 |  15.0/15          |   8.0/15          |  10.8/15          |  10.0/10          |  13.8/15          |   6.2/15          |  14.8/15          |

**Aggregate Mean: 77.9/100**

### celery

```
D1 Uniqueness        ████████████████████  15.0/15
D2 Distribution      ███████████░░░░░░░░░   8.3/15
D3 InfraAccuracy     ██████████████░░░░░░  10.6/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ███████████████░░░░░  11.4/15
D6 DepIntegrity      ██████░░░░░░░░░░░░░░   5.1/15
D7 NamingQuality     ███████████████████░  14.8/15
```

### fastapi

```
D1 Uniqueness        ████████████████████  15.0/15
D2 Distribution      ███████████░░░░░░░░░   8.5/15
D3 InfraAccuracy     ██████████████░░░░░░  10.8/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ███████████████████░  14.8/15
D6 DepIntegrity      █████████░░░░░░░░░░░   7.1/15
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
D1 Uniqueness        ████████████████████  15.0/15
D2 Distribution      ██████████████░░░░░░  10.5/15
D3 InfraAccuracy     █████░░░░░░░░░░░░░░░   4.3/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ████████████░░░░░░░░   9.4/15
D6 DepIntegrity      ████████████████████  15.0/15
D7 NamingQuality     ███████████████████░  14.3/15
```

### scrapy

```
D1 Uniqueness        ████████████████████  15.0/15
D2 Distribution      ██████████░░░░░░░░░░   8.0/15
D3 InfraAccuracy     ██████████████░░░░░░  10.8/15
D4 Coverage          ████████████████████  10.0/10
D5 DirCoherence      ██████████████████░░  13.8/15
D6 DepIntegrity      ████████░░░░░░░░░░░░   6.2/15
D7 NamingQuality     ███████████████████░  14.8/15
```

## Before / After Comparison

| Repo                 |  Before |   After |   Delta |
|----------------------|---------|---------|---------|
| celery               |    74.5 |    75.2 | +   0.8 |
| fastapi              |    77.2 |    81.2 | +   4.0 |
| flask                |    76.1 |    76.1 | +   0.0 |
| rich                 |    75.0 |    78.5 | +   3.5 |
| scrapy               |    77.8 |    78.6 | +   0.8 |
| **Mean**             |    76.1 |    77.9 | +   1.8 |

## Weakest Dimensions

1. **D6 DepIntegrity**: avg 8.1/15 (54%)
   - celery: 5.1
   - fastapi: 7.1
   - flask: 7.2
   - rich: 15.0
   - scrapy: 6.2
2. **D2 Distribution**: avg 8.7/15 (58%)
   - celery: 8.3
   - fastapi: 8.5
   - flask: 8.1
   - rich: 10.5
   - scrapy: 8.0
3. **D3 InfraAccuracy**: avg 9.2/15 (61%)
   - celery: 10.6
   - fastapi: 10.8
   - flask: 9.6
   - rich: 4.3
   - scrapy: 10.8

## Actionable Recommendations

- When splitting cones, prefer cuts that don't break strong call/inherit dependency edges.
- Tune shared_threshold and BFS parameters to reduce single-file cones and prevent mega-cones.
- Improve hub detection with out-degree ratio filter to distinguish functional modules from utilities.
