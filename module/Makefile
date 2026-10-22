obj-m += snd-soc-sof_es8336.o
snd-soc-sof_es8336-y := sof_es8336.o
KVER ?= $(shell uname -r)
KDIR ?= /lib/modules/$(KVER)/build
# Respect explicit remote toolchains; otherwise follow the target kernel.
ifeq ($(origin LLVM),undefined)
ifneq ($(shell grep '^CONFIG_CC_IS_CLANG=y' $(KDIR)/.config 2>/dev/null),)
LLVM := 1
export LLVM
endif
endif

.PHONY: all clean
all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
