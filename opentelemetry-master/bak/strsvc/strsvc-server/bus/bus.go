package bus

import "strings"

func Count(str string) int64 {
	return int64(len(str))
}

func Uppercase(str string) string {
	return strings.ToUpper(str)
}
