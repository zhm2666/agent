package bus

import (
	"context"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/metric"
)

type metricBus struct {
	sumCounter    metric.Int64Counter
	concatCounter metric.Int64Counter
	sumHistogram  metric.Int64Histogram
	Next          Bus
}

func MetricMiddleware(bus Bus, sumCounter metric.Int64Counter, concatCounter metric.Int64Counter, sumHistogram metric.Int64Histogram) Bus {
	return &metricBus{
		sumCounter:    sumCounter,
		concatCounter: concatCounter,
		sumHistogram:  sumHistogram,
		Next:          bus,
	}
}

func (bus *metricBus) Sum(ctx context.Context, a, b int64) int64 {
	bus.sumCounter.Add(ctx, 1)
	c := bus.Next.Sum(ctx, a, b)
	bus.sumHistogram.Record(ctx, c, metric.WithAttributes(attribute.Int64("a", a), attribute.Int64("b", b), attribute.Int64("c", c)))
	return c
}

func (bus *metricBus) Concat(ctx context.Context, a, b string) string {
	bus.concatCounter.Add(ctx, 1)
	return bus.Next.Concat(ctx, a, b)
}
