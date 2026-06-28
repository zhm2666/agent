package server

import (
	"context"
	"strsvc/proto"
	"strsvc/strsvc-server/bus"
)

type strSvc struct {
	proto.UnimplementedStrServer
}

func NewStrSvc() proto.StrServer {
	return &strSvc{}
}

func (s *strSvc) Count(ctx context.Context, in *proto.CountRequest) (*proto.CountReply, error) {
	count := bus.Count(in.Str)
	return &proto.CountReply{
		V: count,
	}, nil
}
func (s *strSvc) Uppercase(ctx context.Context, in *proto.UppercaseRequest) (*proto.UppercaseReply, error) {
	str := bus.Uppercase(in.Str)
	return &proto.UppercaseReply{
		V: str,
	}, nil
}
