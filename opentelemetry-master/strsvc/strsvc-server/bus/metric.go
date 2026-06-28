package bus

import (
	"context"
	"go.opentelemetry.io/otel/metric"
)

type metricBus struct {
	countCounter     metric.Int64Counter
	uppercaseCounter metric.Int64Counter
	countHistogram   metric.Int64Histogram
	Next             Bus
}

func MetricMiddleware(bus Bus, countCounter metric.Int64Counter, uppercaseCounter metric.Int64Counter, countHistogram metric.Int64Histogram) Bus {
	return &metricBus{
		countCounter:     countCounter,
		uppercaseCounter: uppercaseCounter,
		countHistogram:   countHistogram,
		Next:             bus,
	}
}

func (bus *metricBus) Count(ctx context.Context, str string) int64 {
	bus.countCounter.Add(ctx, 1)
	count := bus.Next.Count(ctx, str)
	bus.countHistogram.Record(ctx, count)
	return count
}

func (bus *metricBus) Uppercase(ctx context.Context, str string) string {
	bus.uppercaseCounter.Add(ctx, 1)
	return bus.Next.Uppercase(ctx, str)
}
