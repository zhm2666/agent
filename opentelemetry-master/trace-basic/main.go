package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/jaeger"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/exporters/zipkin"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.20.0"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
	"time"
	"trace-basic/bus"
)

var (
	otlpGrpcEndpoint = flag.String("otlp-grpc", "", "otlp协议http导出地址，例如：192.168.239.154:4317")
	otlpHttpEndpoint = flag.String("otlp-http", "", "otlp协议http导出地址，例如：192.168.239.154:4318")
	jaegerEndpoint   = flag.String("jaeger", "", "jaeger导出地址，例如：http://192.168.239.154:14268/api/traces")
	zipkinEndpoint   = flag.String("zipkin", "", "zipkin导出地址，例如：http://192.168.239.154:9411/api/v2/spans")
)

func main() {
	flag.Parse()
	//初始化provider
	shutDown, err := initProvider(*otlpGrpcEndpoint, *otlpHttpEndpoint, *jaegerEndpoint, *zipkinEndpoint)
	if err != nil {
		log.Fatal(err)
	}
	defer shutDown(context.Background())

	ctx := context.Background()
	//创建main包的tracer
	mainTracer := otel.Tracer("main-tracer")
	ctx, span := mainTracer.Start(ctx, "main", trace.WithAttributes(attribute.Key("method").String("main.main")))
	defer span.End()
	//创建bus包的tracer,传递给bus包
	busTracer := otel.Tracer("bus-tracer")
	b := bus.NewBus(busTracer)
	for i := 0; i < 5; i++ {
		c := b.Sum(ctx, i, i+1)
		fmt.Println(c)
		<-time.After(time.Millisecond * 150)
		c = b.Product(ctx, i, i+1)
		fmt.Println(c)
		<-time.After(time.Millisecond * 150)
	}
	span.RecordError(errors.New("这里报错了"))
	span.SetStatus(codes.Error, "main函数异常")
}

// 1. 初始添加到provider的资源信息
// 2. 初始化Exporter导出器
// 3. 初始化tracer provider
// 4. 设置全局的tracer provider
func initProvider(otlpGrpcEndpoint, otlpHttpEndpoint, jaegerEndpoint, zipkinEndpoint string) (func(ctx context.Context) error, error) {
	ctx := context.Background()
	//初始化资源
	res, err := resource.New(
		ctx, resource.WithOS(),
		resource.WithHost(),
		resource.WithAttributes(
			semconv.ServiceName("trace-basic"),
			semconv.ServiceVersion("1.0.0"),
			attribute.String("env", "dev"),
			attribute.String("author", "nick"),
		))
	if err != nil {
		log.Println(err)
		return nil, err
	}
	//初始化导出器
	var traceExporter sdktrace.SpanExporter
	{
		ctx, cancel := context.WithTimeout(ctx, time.Second)
		defer cancel()
		if otlpGrpcEndpoint != "" {
			conn, err := grpc.DialContext(ctx, otlpGrpcEndpoint,
				grpc.WithTransportCredentials(insecure.NewCredentials()),
				grpc.WithBlock(),
			)
			if err != nil {
				log.Println(err)
				return nil, err
			}
			traceExporter, err = otlptracegrpc.New(ctx, otlptracegrpc.WithGRPCConn(conn), otlptracegrpc.WithInsecure())
			if err != nil {
				log.Println(err)
				return nil, err
			}
		} else if otlpHttpEndpoint != "" {
			traceExporter, err = otlptracehttp.New(ctx, otlptracehttp.WithEndpoint(otlpHttpEndpoint), otlptracehttp.WithInsecure())
			if err != nil {
				log.Println(err)
				return nil, err
			}
		} else if jaegerEndpoint != "" {
			traceExporter, err = jaeger.New(jaeger.WithCollectorEndpoint(jaeger.WithEndpoint(jaegerEndpoint)))
			if err != nil {
				log.Println(err)
				return nil, err
			}
		} else if zipkinEndpoint != "" {
			traceExporter, err = zipkin.New(zipkinEndpoint)
			if err != nil {
				log.Println(err)
				return nil, err
			}
		} else {
			err = errors.New("没有可用exporter端点")
			log.Println(err)
			return nil, err
		}
	}
	// 初始化provider
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(sdktrace.NewBatchSpanProcessor(traceExporter)),
	)
	// 设置全局provider
	otel.SetTracerProvider(tracerProvider)
	return tracerProvider.Shutdown, nil
}
