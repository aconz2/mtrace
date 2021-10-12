#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>

int main(int argc, char **argv) {
	size_t n = atol(argv[1]);
	char *buf = (char *)malloc(n);
	for (size_t i = 0; i < n; i++) {
		buf[i] ^= 13;
	}

	char buf2[1024];
	FILE *f = fopen("/proc/self/status", "r");
	for (;;) {
		int i = fread(buf2, 1024, 1, f);
		if (i <= 0) break;
		printf("%s", buf2);
	}
  printf("\na.out pid=%d ppid=%d\n", getpid(), getppid());
}
