# 文件API文档
文件的URL地址，不支持Base64编码图片文件。支持PDF、Word等格式，最多支持50个。

## 文件列表

> 获取已上传文件的分页列表，支持按用途和排序过滤。

### OpenAPI

````yaml openapi/openapi.json get /paas/v4/files
paths:
  path: /paas/v4/files
  method: get
  servers:
    - url: https://open.bigmodel.cn/api/
      description: 开放平台服务
  request:
    security:
      - title: bearerAuth
        parameters:
          query: {}
          header:
            Authorization:
              type: http
              scheme: bearer
              description: >-
                使用以下格式进行身份验证：Bearer [<your api
                key>](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)
          cookie: {}
    parameters:
      path: {}
      query:
        after:
          schema:
            - type: string
              description: 分页游标
        purpose:
          schema:
            - type: enum<string>
              enum:
                - batch
                - file-extract
                - code-interpreter
                - agent
              required: true
              description: 按用途过滤文件
        order:
          schema:
            - type: enum<string>
              enum:
                - created_at
              description: 排序方式
        limit:
          schema:
            - type: integer
              description: 每页返回的文件数量
              maximum: 100
              minimum: 1
              default: 20
      header: {}
      cookie: {}
    body: {}
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              object:
                allOf:
                  - type: string
                    enum:
                      - list
              data:
                allOf:
                  - type: array
                    items:
                      $ref: '#/components/schemas/FileObject'
              has_more:
                allOf:
                  - type: boolean
                    description: 是否有更多数据
            refIdentifier: '#/components/schemas/FileListResponse'
        examples:
          example:
            value:
              object: list
              data:
                - id: <string>
                  object: file
                  bytes: 123
                  created_at: 123
                  filename: <string>
                  purpose: <string>
              has_more: true
        description: 业务处理成功
    default:
      application/json:
        schemaArray:
          - type: object
            properties:
              error:
                allOf:
                  - required:
                      - code
                      - message
                    type: object
                    properties:
                      code:
                        type: string
                      message:
                        type: string
            refIdentifier: '#/components/schemas/Error'
        examples:
          example:
            value:
              error:
                code: <string>
                message: <string>
        description: 请求失败。
  deprecated: false
  type: path
components:
  schemas:
    FileObject:
      type: object
      properties:
        id:
          type: string
          description: 文件标识符
        object:
          type: string
          enum:
            - file
        bytes:
          type: integer
          description: 文件大小（字节）
        created_at:
          type: integer
          description: 文件创建的`Unix`时间戳
        filename:
          type: string
          description: 文件名
        purpose:
          type: string
          description: 文件的预期用途

````


## 上传文件

> 上传用于 `Batch 任务`、`文件内容抽取`、`智能体` 等功能的文件。注意 `Try it` 功能仅支持小文件上传，实际支持的文件大小请参见下文 `purpose` 相关说明。

### OpenAPI

````yaml openapi/openapi.json post /paas/v4/files
paths:
  path: /paas/v4/files
  method: post
  servers:
    - url: https://open.bigmodel.cn/api/
      description: 开放平台服务
  request:
    security:
      - title: bearerAuth
        parameters:
          query: {}
          header:
            Authorization:
              type: http
              scheme: bearer
              description: >-
                使用以下格式进行身份验证：Bearer [<your api
                key>](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)
          cookie: {}
    parameters:
      path: {}
      query: {}
      header: {}
      cookie: {}
    body:
      multipart/form-data:
        schemaArray:
          - type: object
            properties:
              file:
                allOf:
                  - type: string
                    format: binary
                    description: 要上传的文件
              purpose:
                allOf:
                  - type: string
                    enum:
                      - batch
                      - file-extract
                      - code-interpreter
                      - agent
                      - voice-clone-input
                    description: >-
                      文件的预期用途。

                      `batch`：用于批量任务处理，支持 `.jsonl` 文件格式，，单个文件大小限制为`100
                      MB`，文件数不超过 `1000` 个。`Batch`指南。

                      `file-extract`：用于文档内容抽取，支持的格式包括：`pdf、docx、doc、xls、xlsx、ppt、pptx、png、jpg、jpeg、csv`，单个文件大小限制为
                      `50M`，图片大小不超过`5M`，文件数不超过 `100` 个。

                      `code-interpreter`：文件上传给代码沙盒`CI`使用，支持的格式包括：`pdf、docx、doc、xls、xlsx、txt、png、jpg、jpeg、csv`，单个文件大小限制为
                      `20M`，图片大小不超过`5M`，文件数不超过 `100` 个。

                      `agent`：用于智能体文件上传，支持的格式包括：`pdf、docx、doc、xls、xlsx、txt、png、jpg、jpeg、csv`，单个文件大小限制为
                      `20M`，图片大小不超过`5M`，文件数不超过 `1000` 个。

                      `voice-clone-input`: 用于音色克隆功能示例音频文件的上传。支持的格式包括`mp3、wav`
            required: true
            refIdentifier: '#/components/schemas/FileUploadRequest'
            requiredProperties:
              - file
              - purpose
        examples:
          example:
            value:
              purpose: batch
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              id:
                allOf:
                  - type: string
                    description: 文件标识符
              object:
                allOf:
                  - type: string
                    enum:
                      - file
              bytes:
                allOf:
                  - type: integer
                    description: 文件大小（字节）
              created_at:
                allOf:
                  - type: integer
                    description: 文件创建的`Unix`时间戳
              filename:
                allOf:
                  - type: string
                    description: 文件名
              purpose:
                allOf:
                  - type: string
                    description: 文件的预期用途
            refIdentifier: '#/components/schemas/FileObject'
        examples:
          example:
            value:
              id: <string>
              object: file
              bytes: 123
              created_at: 123
              filename: <string>
              purpose: <string>
        description: 业务处理成功
    default:
      application/json:
        schemaArray:
          - type: object
            properties:
              error:
                allOf:
                  - required:
                      - code
                      - message
                    type: object
                    properties:
                      code:
                        type: string
                      message:
                        type: string
            refIdentifier: '#/components/schemas/Error'
        examples:
          example:
            value:
              error:
                code: <string>
                message: <string>
        description: 请求失败。
  deprecated: false
  type: path
components:
  schemas: {}

````

## 删除文件

> 永久删除指定文件及其所有关联数据。

### OpenAPI

````yaml openapi/openapi.json delete /paas/v4/files/{file_id}
paths:
  path: /paas/v4/files/{file_id}
  method: delete
  servers:
    - url: https://open.bigmodel.cn/api/
      description: 开放平台服务
  request:
    security:
      - title: bearerAuth
        parameters:
          query: {}
          header:
            Authorization:
              type: http
              scheme: bearer
              description: >-
                使用以下格式进行身份验证：Bearer [<your api
                key>](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)
          cookie: {}
    parameters:
      path:
        file_id:
          schema:
            - type: string
              required: true
              description: 文件唯一标识符
      query: {}
      header: {}
      cookie: {}
    body: {}
  response:
    '200':
      application/json:
        schemaArray:
          - type: object
            properties:
              id:
                allOf:
                  - type: string
                    description: 删除的资源`ID`
              object:
                allOf:
                  - type: string
                    description: 资源类型
                  - type: string
                    enum:
                      - file
              deleted:
                allOf:
                  - type: boolean
                    description: 是否成功删除
            refIdentifier: '#/components/schemas/BaseDeletedResponse'
        examples:
          example:
            value:
              id: <string>
              object: file
              deleted: true
        description: 业务处理成功
    default:
      application/json:
        schemaArray:
          - type: object
            properties:
              error:
                allOf:
                  - required:
                      - code
                      - message
                    type: object
                    properties:
                      code:
                        type: string
                      message:
                        type: string
            refIdentifier: '#/components/schemas/Error'
        examples:
          example:
            value:
              error:
                code: <string>
                message: <string>
        description: 请求失败。
  deprecated: false
  type: path
components:
  schemas: {}

````


## 文件内容

> 获取文件内容。只支持 `batch` 与 `file-extract` 文件类型。

### OpenAPI

````yaml openapi/openapi.json get /paas/v4/files/{file_id}/content
paths:
  path: /paas/v4/files/{file_id}/content
  method: get
  servers:
    - url: https://open.bigmodel.cn/api/
      description: 开放平台服务
  request:
    security:
      - title: bearerAuth
        parameters:
          query: {}
          header:
            Authorization:
              type: http
              scheme: bearer
              description: >-
                使用以下格式进行身份验证：Bearer [<your api
                key>](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)
          cookie: {}
    parameters:
      path:
        file_id:
          schema:
            - type: string
              required: true
              description: 被请求的文件的唯一标识符，用于指定要获取内容的特定文件。
      query: {}
      header: {}
      cookie: {}
    body: {}
  response:
    '200':
      application/octet-stream:
        schemaArray:
          - type: file
            contentEncoding: binary
        examples:
          example: {}
        description: 请求成功，返回文件字节流。
    default:
      application/json:
        schemaArray:
          - type: object
            properties:
              error:
                allOf:
                  - required:
                      - code
                      - message
                    type: object
                    properties:
                      code:
                        type: string
                      message:
                        type: string
            refIdentifier: '#/components/schemas/Error'
        examples:
          example:
            value:
              error:
                code: <string>
                message: <string>
        description: 请求失败。
  deprecated: false
  type: path
components:
  schemas: {}

````