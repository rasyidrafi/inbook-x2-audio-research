"""Exercise actual remove/unwind C code with descriptor ownership assertions."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_driver import function

ROOT = Path(__file__).resolve().parents[1]
STUBS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
struct gpio_desc { int releases; };
struct device { int released; };
struct delayed_work { bool cancelled; };
struct sof_es8336_private {
 struct gpio_desc *gpio_speakers, *gpio_headphone;
 struct device *codec_dev;
 struct delayed_work pcm_pop_work;
};
struct snd_soc_card { struct sof_es8336_private *priv; };
struct platform_device { struct snd_soc_card *card; };
static struct snd_soc_card sof_es8336_card;
static struct delayed_work *work;
static int register_result;
#define platform_get_drvdata(p) ((p)->card)
#define snd_soc_card_get_drvdata(c) ((c)->priv)
static void cancel_delayed_work_sync(struct delayed_work *w) { w->cancelled = true; }
static void gpiod_put(struct gpio_desc *g) { if (g) g->releases++; }
static void device_remove_software_node(struct device *d) { (void)d; }
static void put_device(struct device *d) { d->released++; }
static int devm_snd_soc_register_card(struct device *d, struct snd_soc_card *c) {
 (void)d; (void)c; return register_result;
}
#define dev_err(...) ((void)0)
#define platform_set_drvdata(p, c) ((void)(p), (void)(c))
'''


class CleanupTests(unittest.TestCase):
    def compile_run(self, code: str) -> None:
        with tempfile.TemporaryDirectory(prefix='es8326-cleanup-') as directory:
            source, binary = Path(directory) / 'test.c', Path(directory) / 'test'
            source.write_text(code)
            subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-Wno-unused-variable', str(source), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_remove_releases_both_descriptors(self):
        for filename, expected in [('inputs/linux-upstream/sof_es8336.c', 0),
                                   ('module/sof_es8336_modern.c', 1),
                                   ('module/sof_es8336_legacy.c', 1)]:
            with self.subTest(source=filename):
                source = (ROOT / filename).read_text()
                main = r'''
int main(void) {
 struct gpio_desc spk = {0}, hp = {0}; struct device codec = {0};
 struct sof_es8336_private priv = { &spk, &hp, &codec, {false} };
 struct snd_soc_card card = { &priv }; struct platform_device pdev = { &card };
 sof_es8336_remove(&pdev);
 assert(priv.pcm_pop_work.cancelled);
 assert(spk.releases == 1); assert(hp.releases == EXPECTED);
 assert(codec.released == 1);
 return 0;
}
'''.replace('EXPECTED', str(expected))
                self.compile_run(STUBS + function(source, 'sof_es8336_remove') + main)

    def test_probe_failure_unwinds_only_acquired_resources(self):
        for filename in ('module/sof_es8336_modern.c', 'module/sof_es8336_legacy.c'):
            with self.subTest(source=filename):
                source = (ROOT / filename).read_text()
                start = source.index('\tret = devm_snd_soc_register_card(dev, card);')
                end = source.index('\nstatic void sof_es8336_remove', start)
                tail = source[start:end]
                prefix = r'''
static int unwind(struct sof_es8336_private *priv, int scenario) {
 struct device *codec_dev = priv->codec_dev, *dev = codec_dev;
 struct snd_soc_card *card = &sof_es8336_card;
 struct platform_device *pdev = NULL;
 int ret = -1;
 if (scenario == 1) goto err_put_speakers;
 if (scenario == 2) goto err_put_codec;
'''
                main = r'''
int main(void) {
 for (int scenario = 0; scenario < 3; scenario++) {
  struct gpio_desc spk = {0}, hp = {0}; struct device codec = {0};
  struct sof_es8336_private priv = { &spk, &hp, &codec, {false} };
  register_result = -1;
  assert(unwind(&priv, scenario) == -1);
  assert(spk.releases == (scenario != 2));
  assert(hp.releases == (scenario == 0));
  assert(priv.pcm_pop_work.cancelled == (scenario == 0));
  assert(codec.released == 1);
 }
 return 0;
}
'''
                self.compile_run(STUBS + prefix + tail + main)


if __name__ == '__main__':
    unittest.main()
