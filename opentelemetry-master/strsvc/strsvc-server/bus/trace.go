package bus

import (
	"context"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

type traceBus struct {
	tracer trace.Tracer
	Next   Bus
}

func TracerMiddleware(bus Bus, tracer trace.Tracer) Bus {
	return &traceBus{
		tracer: tracer,
		Next:   bus,
	}
}

func (bus *traceBus) Count(ctx context.Context, str string) int64 {
	ctx, span := bus.tracer.Start(ctx, "Count")
	defer span.End()
	count := bus.Next.Count(ctx, str)
	span.SetAttributes(attribute.String("str", str), attribute.Int64("count", count))
	return count
}

func (bus *traceBus) Uppercase(ctx context.Context, str string) string {
	ctx, span := bus.tracer.Start(ctx, "Uppercase")
	defer span.End()
	uppercase := bus.Next.Uppercase(ctx, str)
	span.SetAttributes(attribute.String("str", str), attribute.String("uppercase", uppercase))
	return uppercase
}
