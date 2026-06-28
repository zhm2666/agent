package main

import (
	"context"
	"fmt"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
	"strsvc/proto"
)

func main() {
	count()
	uppercase()
}

func count() {
	conn, err := grpc.Dial("localhost:50052", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	client := proto.NewStrClient(conn)
	ctx := context.Background()
	in := &proto.CountRequest{
		Str: "abcdefghigk",
	}
	res, err := client.Count(ctx, in)
	if err != nil {
		log.Println(err)
		return
	}
	fmt.Println(res)
}
func uppercase() {
	conn, err := grpc.Dial("localhost:50052", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	client := proto.NewStrClient(conn)
	ctx := context.Background()
	in := &proto.UppercaseRequest{
		Str: "abcdefghijk",
	}
	res, err := client.Uppercase(ctx, in)
	if err != nil {
		log.Println(err)
		return
	}
	fmt.Println(res)
}
