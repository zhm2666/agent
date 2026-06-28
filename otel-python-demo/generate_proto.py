"""
Script to generate Python gRPC code from proto files.
Run this script after modifying proto definitions.
"""
import subprocess
import os

def main():
    print("Generating gRPC code from proto files...")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate strsvc proto
    print("\n1. Generating strsvc.proto...")
    result = subprocess.run([
        "python", "-m", "grpc_tools.protoc",
        f"-I./proto",
        "--python_out=./strsvc",
        "--grpc_python_out=./strsvc",
        "./proto/strsvc.proto"
    ], cwd=base_dir, capture_output=True, text=True)

    if result.returncode == 0:
        print("   strsvc.proto generated successfully!")
    else:
        print(f"   Error: {result.stderr}")

    # Generate addsvc proto
    print("\n2. Generating addsvc.proto...")
    result = subprocess.run([
        "python", "-m", "grpc_tools.protoc",
        f"-I./proto",
        "--python_out=./addsvc",
        "--grpc_python_out=./addsvc",
        "./proto/addsvc.proto"
    ], cwd=base_dir, capture_output=True, text=True)

    if result.returncode == 0:
        print("   addsvc.proto generated successfully!")
    else:
        print(f"   Error: {result.stderr}")

    print("\nProto generation complete!")
    print("\nNote: You may need to fix imports in generated files.")
    print("Replace 'import strsvc_pb2 as strsvc__pb2' with 'from . import strsvc_pb2'")

if __name__ == "__main__":
    main()
