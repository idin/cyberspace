# Internet

## Wikipedia

### InfoBox

```python
from internet import Wikipedia
w = Wikipedia(rate_limit_wait_seconds=0.1)
result = w.search('steve wozniak')[0]
print(result)
```
**output**
```json
{
  "title_1": "Steve Wozniak",
  "unknown_row_1": {
    "texts": [
      "Wozniak in 2018"
    ],
    "links": [
      {
        "url": "/wiki/File:Steve_Wozniak,_November_2018.jpg"
      }
    ]
  },
  "Born": {
    "texts": [
      "Stephen Gary Wozniak[1](p18) (1950-08-11) August 11, 1950 (age 68)San Jose, California, U.S."
    ],
    "links": [
      {
        "url": "#cite_note-iWoz-1",
        "text": "[1]"
      },
      {
        "title": "San Jose, California",
        "url": "/wiki/San_Jose,_California",
        "text": "San Jose"
      },
      {
        "title": "California",
        "url": "/wiki/California",
        "text": "California"
      }
    ]
  },
  ...
```