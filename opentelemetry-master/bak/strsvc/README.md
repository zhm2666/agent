# 生成代码
``` 
protoc --go_out . --go_opt paths=source_relative proto/strsvc.proto
protoc --go-grpc_out . --go-grpc_opt paths=source_relative proto/strsvc.proto
```
# 依赖安装
``` 
go mod tidy
```