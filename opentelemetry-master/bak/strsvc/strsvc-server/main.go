package main

import (
	"google.golang.org/grpc"
	"log"
	"net"
	"strsvc/proto"
	"strsvc/strsvc-server/server"
)

func main() {
	lis, err := net.Listen("tcp", ":50052")
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer()
	proto.RegisterStrServer(s, server.NewStrSvc())
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
