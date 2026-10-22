// SPDX-License-Identifier: GPL-2.0-only
#include <linux/version.h>
#if LINUX_VERSION_CODE >= KERNEL_VERSION(7, 2, 0)
#include "sof_es8336_modern.c"
#else
#include "sof_es8336_legacy.c"
#endif
