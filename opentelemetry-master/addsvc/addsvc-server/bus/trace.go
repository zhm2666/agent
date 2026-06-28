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

func (bus *traceBus) Sum(ctx context.Context, a, b int64) int64 {
	ctx, span := bus.tracer.Start(ctx, "Sum")
	defer span.End()
	c := bus.Next.Sum(ctx, a, b)
	span.SetAttributes(attribute.Int64("a", a), attribute.Int64("b", b), attribute.Int64("c", c))
	return c
}

func (bus *traceBus) Concat(ctx context.Context, a, b string) string {
	ctx, span := bus.tracer.Start(ctx, "Concat")
	defer span.End()
	c := bus.Next.Concat(ctx, a, b)
	span.SetAttributes(attribute.String("a", a), attribute.String("b", b), attribute.String("c", c))
	return c
}
