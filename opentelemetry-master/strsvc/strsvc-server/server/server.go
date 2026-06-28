package server

import (
	"context"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/baggage"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc/metadata"
	"strsvc/proto"
	"strsvc/strsvc-server/bus"
)

type strSvc struct {
	proto.UnimplementedStrServer
	bus        bus.Bus
	tracer     trace.Tracer
	propagator propagation.TextMapPropagator
}

func NewStrSvc(bus bus.Bus, tracer trace.Tracer, propagator propagation.TextMapPropagator) proto.StrServer {
	return &strSvc{
		bus:        bus,
		tracer:     tracer,
		propagator: propagator,
	}
}

func (s *strSvc) Count(ctx context.Context, in *proto.CountRequest) (*proto.CountReply, error) {
	md, _ := metadata.FromIncomingContext(ctx)
	mp := propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]
	}
	ctx = s.propagator.Extract(ctx, mp)

	ctx, span := s.tracer.Start(ctx, "strsvc.Count")
	defer span.End()
	count := s.bus.Count(ctx, in.Str)
	return &proto.CountReply{
		V: count,
	}, nil
}
func (s *strSvc) Uppercase(ctx context.Context, in *proto.UppercaseRequest) (*proto.UppercaseReply, error) {
	md, _ := metadata.FromIncomingContext(ctx)
	mp := propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]
	}
	ctx = s.propagator.Extract(ctx, mp)

	//从上下文中获取自定义的baggage信息
	b := baggage.FromContext(ctx)

	ctx, span := s.tracer.Start(ctx, "strsvc.Uppercase")
	defer span.End()
	span.SetAttributes(attribute.String("author", b.Member("author").Value()), attribute.String("org", b.Member("org").Value()))
	str := s.bus.Uppercase(ctx, in.Str)
	return &proto.UppercaseReply{
		V: str,
	}, nil
}
