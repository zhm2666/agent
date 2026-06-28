package main

import (
	"addsvc/addsvc-server/bus"
	"addsvc/addsvc-server/server"
	"addsvc/proto"
	strProto "addsvc/services/strsvc/proto"
	"context"
	"flag"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	api "go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.20.0"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
	"net"
	"time"
)

var otlpGrpcEndpoint = flag.String("otlp-grpc", "192.168.239.154:5317", "otlp协议http导出地址，例如：192.168.239.154:4317")
var strSvcEndpoint = flag.String("strsvc-endpoint", "localhost:50052", "strsvc服务的grpc地址")

func main() {
	flag.Parse()
	tracerShutdown, err := initTracerProvider(*otlpGrpcEndpoint)
	if err != nil {
		log.Fatal(err)
	}
	defer tracerShutdown(context.Background())
	meterShutdown, err := initMeterProvider(*otlpGrpcEndpoint)
	if err != nil {
		log.Fatal(err)
	}
	defer meterShutdown(context.Background())
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer()

	conn, err := grpc.Dial(*strSvcEndpoint, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	strClient := strProto.NewStrClient(conn)

	bus, tracer := getBus()
	propagator := otel.GetTextMapPropagator()
	proto.RegisterAddServer(s, server.NewAddSvc(bus, tracer, strClient, propagator))
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}

// 1. 初始添加到provider的资源信息
// 2. 初始化Exporter导出器
// 3. 初始化tracer provider
// 4. 设置全局的tracer provider
// 5. 设置全局的传播程序
func initTracerProvider(otlpGrpcEndpoint string) (func(ctx context.Context) error, error) {
	ctx := context.Background()
	//初始化资源
	res, err := resource.New(
		ctx, resource.WithOS(),
		resource.WithHost(),
		resource.WithAttributes(
			semconv.ServiceName("add-service"),
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
	}
	// 初始化provider
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(sdktrace.NewBatchSpanProcessor(traceExporter)),
	)
	// 设置全局provider
	otel.SetTracerProvider(tracerProvider)
	//TraceContext 传播程序用于传播traceparent 和 tracestate标头，确保跟踪不会被破坏
	//Baggage 传播程序用于传播与跟踪相关的用户自定义信息
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
	return tracerProvider.Shutdown, nil
}

// 1. 初始添加到provider的资源信息
// 2. 初始化Exporter与Reader导出器
// 3. 初始化meter provider
// 4. 设置全局的meter provider
func initMeterProvider(otlpGrpcEndpoint string) (func(ctx context.Context) error, error) {
	ctx := context.Background()
	//初始化资源
	res, err := resource.New(
		ctx, resource.WithOS(),
		resource.WithHost(),
		resource.WithAttributes(
			semconv.ServiceName("add-service"),
			semconv.ServiceVersion("1.0.0"),
			attribute.String("env", "dev"),
			attribute.String("author", "nick"),
		))
	if err != nil {
		log.Println(err)
		return nil, err
	}
	//初始化Exporter与Reader导出器
	var metricReader metric.Reader
	{
		conn, err := grpc.DialContext(ctx, otlpGrpcEndpoint,
			grpc.WithTransportCredentials(insecure.NewCredentials()),
			grpc.WithBlock(),
		)
		if err != nil {
			log.Println(err)
			return nil, err
		}
		exporter, err := otlpmetricgrpc.New(ctx, otlpmetricgrpc.WithGRPCConn(conn), otlpmetricgrpc.WithInsecure())
		if err != nil {
			log.Println(err)
			return nil, err
		}
		metricReader = metric.NewPeriodicReader(exporter, metric.WithInterval(time.Second*5))
	}

	//初始化provider
	provider := metric.NewMeterProvider(metric.WithResource(res), metric.WithReader(metricReader))
	//设置全局provider
	otel.SetMeterProvider(provider)
	return provider.Shutdown, nil
}

func getBus() (bus.Bus, trace.Tracer) {
	tracer := otel.Tracer("addsvc")
	b := bus.NewBus()
	b = bus.TracerMiddleware(b, tracer)
	meter := otel.Meter("addsvc")
	sumCounter, err := meter.Int64Counter("sum", api.WithDescription("sum 函数累计调用次数"))
	if err != nil {
		log.Fatal(err)
	}

	concatCounter, err := meter.Int64Counter("concat", api.WithDescription("concat 函数累计调用次数"))
	if err != nil {
		log.Fatal(err)
	}
	sumHistogram, err := meter.Int64Histogram("sum_histogram", api.WithDescription("sum 函数求和结果分布"))
	if err != nil {
		log.Fatal(err)
	}
	b = bus.MetricMiddleware(b, sumCounter, concatCounter, sumHistogram)
	return b, tracer
}
