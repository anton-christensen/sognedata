# Building
`docker build -t sognedata .`

# Running
To run the api on port 5000 and persisting the dataset for faster startup

`docker run --rm -p 5000:80 -v $(pwd)/data:/usr/src/app/data sognedata`

# API documentation

| Method | Endpoint               | Response                                                                  |
| ------ | ---------------------- | ------------------------------------------------------------------------- |
| GET    | [`/<id>               `](/601                ) | The sogn, stift or provsti with the given id      |
| GET    | [`/<lat>/<lon>        `](/57.04/9.939        ) | Stift, provstier and sogne that contain the point |
| GET    | [`/stift/<lat>/<lon>  `](/stift/57.04/9.939  ) | The stift that contains the point                 |
| GET    | [`/provsti/<lat>/<lon>`](/provsti/57.04/9.939) | The provsti that contains the point               |
| GET    | [`/sogn/<lat>/<lon>   `](/sogn/57.04/9.939   ) | The sogn that contains the point                  |
| GET    | [`/stift              `](/stift              ) | All the stifts                                    |
| GET    | [`/provsti            `](/provsti            ) | All the provstier                                 |
| GET    | [`/sogn               `](/sogn               ) | All the sogne                                     |
| GET    | [`/stift/<id>         `](/stift/1            ) | The stift with the given id                       |
| GET    | [`/provsti/<id>       `](/provsti/601        ) | The provsti with the given id                     |
| GET    | [`/sogn/<id>          `](/sogn/8369          ) | The sogn with the given id                        |
| GET    | [`/stift/<id>/provsti `](/stift/1/provsti    ) | All the provstier of the stift with the given id  |
| GET    | [`/stift/<id>/sogn    `](/stift/1/sogn       ) | All the sogn of the stift with the given id       |
| GET    | [`/provsti/<id>/sogn  `](/provsti/601/sogn   ) | All the sogne of the provsti with the given id    |
|        |                                                |                                                   |
|   -    |                                                |                                                   |
|        |                                                |                                                   |
| GET    | [`<endpoint>/geometry `](/l3/57.04/9.939/geometry) | Returns the same data + geometry              |

**l1, l2 and l3 can be used instead of stift, provsti and sogn respectively**


## Other routes

| Route                  | Description                                     |
| ---------------------- | ----------------------------------------------- |
| [`/static/map.html    `](/static/map.html    ) | Map view for testing    |
| [`/data/dataset.json  `](/data/dataset.json  ) | JSON version of dataset |
