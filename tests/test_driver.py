#!/usr/bin/env python3
"""Compile actual driver functions with deterministic GPIO/workqueue substitutes.

This covers sequential state transitions, not kernel scheduling races or hardware.
Run on the build host: python3 tests/test_driver.py
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(source: str, name: str) -> str:
    start = source.index("static ", source.rfind("\n}", 0, source.index(name)) + 2)
    opening = source.index("{", source.index(name, start))
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <stdio.h>
#define SOF_ES8336_HEADPHONE_GPIO 128
#define SNDRV_PCM_STREAM_PLAYBACK 0
#define SNDRV_PCM_TRIGGER_START 1
#define SNDRV_PCM_TRIGGER_PAUSE_RELEASE 2
#define SNDRV_PCM_TRIGGER_RESUME 3
#define SNDRV_PCM_TRIGGER_PAUSE_PUSH 4
#define SNDRV_PCM_TRIGGER_SUSPEND 5
#define SNDRV_PCM_TRIGGER_STOP 6
#define system_dfl_wq 0
#define system_wq 0
#define msecs_to_jiffies(ms) (ms)
#define container_of(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))
static unsigned long quirk;
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; bool pending; unsigned int delay; };
struct gpio_desc { int value; unsigned int writes; };
struct sof_es8336_private {
    struct gpio_desc *gpio_speakers, *gpio_headphone;
    bool speaker_en, headphone_gpio_follows_speaker;
    struct delayed_work pcm_pop_work;
};
struct snd_soc_card { struct sof_es8336_private *priv; };
struct snd_soc_pcm_runtime { struct snd_soc_card *card; };
struct snd_pcm_substream { int stream; struct snd_soc_pcm_runtime *rtd; };
#define snd_soc_substream_to_rtd(s) ((s)->rtd)
#define snd_soc_card_get_drvdata(c) ((c)->priv)
static void gpiod_set_value_cansleep(struct gpio_desc *gpio, int value) {
    if (gpio) { gpio->value = value; gpio->writes++; }
}
static bool queue_delayed_work(int queue, struct delayed_work *work, unsigned int delay) {
    (void)queue;
    if (work->pending) return false;
    work->pending = true;
    work->delay = delay;
    return true;
}
static bool cancel_delayed_work(struct delayed_work *work) {
    bool was_pending = work->pending;
    work->pending = false;
    return was_pending;
}
'''

HARNESS = r'''
static void run_work(struct sof_es8336_private *priv) {
    if (!priv->pcm_pop_work.pending) return;
    assert(priv->pcm_pop_work.delay == 70);
    priv->pcm_pop_work.pending = false;
    pcm_pop_work_events(&priv->pcm_pop_work.work);
}
int main(void) {
    unsigned int cases = 0;
    for (int board = 0; board < 2; board++)
    for (int stream = 0; stream < 2; stream++)
    for (int powered = 0; powered < 2; powered++)
    for (int stop = 4; stop <= 6; stop++)
    for (int start = 1; start <= 3; start++) {
        struct gpio_desc spk = {0}, hp = {0};
        struct sof_es8336_private priv = {
            .gpio_speakers = &spk, .gpio_headphone = &hp,
            .speaker_en = !powered, .headphone_gpio_follows_speaker = board,
        };
        struct snd_soc_card card = { &priv };
        struct snd_soc_pcm_runtime rtd = { &card };
        struct snd_pcm_substream sub = { stream, &rtd };
        quirk = SOF_ES8336_HEADPHONE_GPIO;
        pcm_pop_work_events(&priv.pcm_pop_work.work);
        assert(spk.value == !powered);
        assert(hp.value == (EXPECT_POLARITY && board ? !powered : powered));
        assert(sof_8336_trigger(&sub, stop) == 0);
        int stopped_value = spk.value;
        assert(sof_8336_trigger(&sub, start) == 0);
        bool should_queue = EXPECT_RESTART && board && !stream && powered;
        assert(priv.pcm_pop_work.pending == should_queue);
        run_work(&priv);
        assert(spk.value == (should_queue ? 0 : stopped_value));
        if (board && !stream && powered) {
            // Negative controls must reproduce the muted amplifier after START.
            assert(spk.value == (EXPECT_RESTART ? 0 : 1));
            for (int cycle = 0; cycle < 3; cycle++) {
                assert(sof_8336_trigger(&sub, stop) == 0);
                assert(sof_8336_trigger(&sub, start) == 0);
                run_work(&priv);
                assert(spk.value == (EXPECT_RESTART ? 0 : 1));
            }
            // STOP cancels a queued enable before its 70ms delay expires.
            assert(sof_8336_trigger(&sub, start) == 0);
            assert(sof_8336_trigger(&sub, stop) == 0);
            assert(!priv.pcm_pop_work.pending);
            run_work(&priv);
            assert(spk.value == 1);
        }
        assert(sof_8336_trigger(&sub, 999) == -EINVAL);
        cases++;
    }
    printf("%u sequential transition cases passed; restart_fix=%d polarity_fix=%d\n",
           cases, EXPECT_RESTART, EXPECT_POLARITY);
    return 0;
}
'''


def main() -> None:
    sources = [
        ("upstream-negative-control", ROOT / "inputs/linux-upstream/sof_es8336.c", 0, 0),
        ("modern-candidate", ROOT / "module/sof_es8336_modern.c", 1, 1),
        ("legacy-candidate", ROOT / "module/sof_es8336_legacy.c", 1, 1),
    ]
    for name, path, restart, polarity in sources:
        source = path.read_text()
        actual = '\n'.join(function(source, name) for name in
                           ("pcm_pop_work_events", "sof_8336_trigger"))
        with tempfile.TemporaryDirectory(prefix="es8326-test-") as temp:
            cfile = Path(temp) / "test.c"
            binary = Path(temp) / "test"
            cfile.write_text(STUBS + actual + HARNESS)
            subprocess.run(["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                            "-Wno-unused-function", f"-DEXPECT_RESTART={restart}",
                            f"-DEXPECT_POLARITY={polarity}", str(cfile), "-o", str(binary)],
                           check=True)
            result = subprocess.run([str(binary)], check=True, text=True, capture_output=True)
            print(f"{name}: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
