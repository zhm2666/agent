package main

import (
	"context"
	"flag"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetricgrpc"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/exporters/prometheus"
	api "go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/sdk/instrumentation"
	"go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/metric/aggregation"
	"go.opentelemetry.io/otel/sdk/resource"
	semconv "go.opentelemetry.io/otel/semconv/v1.20.0"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"time"
)

var (
	otlpGrpcEndpoint = flag.String("otlp-grpc", "", "otlp协议http导出地址，例如：192.168.239.154:4317")
	otlpHttpEndpoint = flag.String("otlp-http", "", "otlp协议http导出地址，例如：192.168.239.154:4318")
)

func main() {
	flag.Parse()
	ctx := context.Background()
	//初始化meter provider 全局仅初始化一次
	shutdown, err := initProvider(*otlpGrpcEndpoint, *otlpHttpEndpoint)
	if err != nil {
		log.Fatal(err)
	}
	defer shutdown(ctx)
	//通过provider创建meter，可以基于应用或服务创建，也可以基于lib库或者模块创建
	//通过meter创建具体的指标（counter、gauge、直方图（histogram））
	getMetrics()

	//启动promhttp
	if *otlpGrpcEndpoint == "" && *otlpHttpEndpoint == "" {
		go serveMetrics()
	}

	ctx, stop := signal.NotifyContext(ctx, os.Kill, os.Interrupt)
	defer stop()
	<-ctx.Done()
}

// 1. 初始添加到provider的资源信息
// 2. 初始化Exporter与Reader导出器
// 3. 初始化meter provider
// 4. 设置全局的meter provider
func initProvider(otlpGrpcEndpoint, otlpHttpEndpoint string) (func(ctx context.Context) error, error) {
	ctx := context.Background()
	//初始化资源
	res, err := resource.New(
		ctx, resource.WithOS(),
		resource.WithHost(),
		resource.WithAttributes(
			semconv.ServiceName("meter-basic"),
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
		if otlpGrpcEndpoint != "" {
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
		} else if otlpHttpEndpoint != "" {
			exporter, err := otlpmetrichttp.New(ctx, otlpmetrichttp.WithEndpoint(otlpHttpEndpoint), otlpmetrichttp.WithInsecure())
			if err != nil {
				log.Println(err)
				return nil, err
			}
			metricReader = metric.NewPeriodicReader(exporter, metric.WithInterval(time.Second*5))
		} else {
			//初始化prometheus导出器
			metricReader, err = prometheus.New()
			if err != nil {
				log.Println(err)
				return nil, err
			}
		}
	}
	view := metric.NewView(metric.Instrument{
		//指定作用的指标名称
		Name: "custom_histogram",
		//作用该范围，仅针对 metric-basic-meter
		Scope: instrumentation.Scope{Name: "metric-basic-meter"},
	}, metric.Stream{
		Name: "myhistogram",
		Aggregation: aggregation.ExplicitBucketHistogram{
			Boundaries: []float64{2, 4, 8, 16, 32, 64, 128, 256, 512},
		},
	})

	//初始化provider
	provider := metric.NewMeterProvider(metric.WithResource(res), metric.WithReader(metricReader), metric.WithView(view))
	//设置全局provider
	otel.SetMeterProvider(provider)
	return provider.Shutdown, nil
}

// 获取自定义指标
func getMetrics() {
	ctx := context.Background()
	meter := otel.Meter("metric-basic-meter")
	attrs := []attribute.KeyValue{
		attribute.Key("A").String("B"),
		attribute.Key("C").String("D"),
	}
	// counter ,累计指标
	counter, err := meter.Float64Counter("counter", api.WithDescription("累计指标"))
	if err != nil {
		log.Fatal(err)
	}
	counter.Add(ctx, 5, api.WithAttributes(attrs...))
	// 异步counter，每次收集数据的时候获取最新值
	_, err = meter.Float64ObservableCounter("counter1",
		api.WithDescription("异步累计指标"),
		api.WithFloat64Callback(func(ctx context.Context, o api.Float64Observer) error {
			o.Observe(float64(time.Now().Unix()))
			return nil
		}))
	if err != nil {
		log.Fatal(err)
	}
	// gauge实时指标，每次收集数据的时候获取当前值
	rng := rand.New(rand.NewSource(time.Now().UnixNano()))
	gauge, err := meter.Float64ObservableGauge("gauge", api.WithDescription("实时指标"))
	if err != nil {
		log.Fatal(err)
	}
	meter.RegisterCallback(func(ctx context.Context, o api.Observer) error {
		n := rng.Intn(100)
		o.ObserveFloat64(gauge, float64(n))
		return nil
	}, gauge)

	// histogram 直方图
	histogram, err := meter.Float64Histogram("histogram", api.WithDescription("直方图（柱状图）"))
	if err != nil {
		log.Fatal(err)
	}
	histogram.Record(ctx, 233)
	histogram.Record(ctx, 23)
	histogram.Record(ctx, 33)
	histogram.Record(ctx, 53)
	histogram.Record(ctx, 253)
	histogram.Record(ctx, 333)
	histogram.Record(ctx, 500)
	histogram.Record(ctx, 1)
	histogram.Record(ctx, 2)

	// histogram 直方图
	cusHistogram, err := meter.Float64Histogram("custom_histogram", api.WithDescription("自定义视图直方图（柱状图）"))
	if err != nil {
		log.Fatal(err)
	}
	cusHistogram.Record(ctx, 233)
	cusHistogram.Record(ctx, 23)
	cusHistogram.Record(ctx, 33)
	cusHistogram.Record(ctx, 53)
	cusHistogram.Record(ctx, 253)
	cusHistogram.Record(ctx, 333)
	cusHistogram.Record(ctx, 500)
	cusHistogram.Record(ctx, 1)
	cusHistogram.Record(ctx, 2)
}

// 启动prometheus 系统指标采集点
func serveMetrics() {
	http.Handle("/metrics", promhttp.Handler())
	err := http.ListenAndServe(":2223", nil)
	if err != nil {
		log.Fatal(err)
	}
}
