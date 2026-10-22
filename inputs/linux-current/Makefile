obj-m += snd-soc-sof_es8336.o
snd-soc-sof_es8336-y := sof_es8336.o

KVER ?= $(shell uname -r)
KDIR := /lib/modules/$(KVER)/build
LLVM_BUILD := $(shell if grep -q '^CONFIG_CC_IS_CLANG=y' $(KDIR)/.config; then echo LLVM=1; fi)

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) $(LLVM_BUILD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) $(LLVM_BUILD) clean
