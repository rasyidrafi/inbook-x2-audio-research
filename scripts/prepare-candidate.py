#!/usr/bin/env python3
"""Generate a reviewable two-patch series and a dual-kernel DKMS candidate."""
from pathlib import Path
import difflib
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = "sound/soc/intel/boards/sof_es8336.c"


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Expected one occurrence: {old!r}")
    return source.replace(old, new, 1)


def detect_board(source: str) -> str:
    entry = '''	{
		.callback = sof_es8336_quirk_cb,
		.matches = {
			DMI_EXACT_MATCH(DMI_SYS_VENDOR, "Infinix"),
			DMI_EXACT_MATCH(DMI_BOARD_NAME,
					"EM_IC325_200B_V1.0 20211012"),
		},
		.driver_data = (void *)SOF_ES8336_HEADPHONE_GPIO,
	},
'''
    return replace_once(source,
        "static const struct dmi_system_id sof_es8336_quirk_table[] = {\n",
        "static const struct dmi_system_id sof_es8336_quirk_table[] = {\n" + entry)


def board_gpio(source: str) -> str:
    source = replace_once(source, "\tbool speaker_en;\n",
                          "\tbool speaker_en;\n\tbool headphone_gpio_follows_speaker;\n")
    source = replace_once(source,
        "\t\tgpiod_set_value_cansleep(priv->gpio_headphone, !priv->speaker_en);",
        "\t\tgpiod_set_value_cansleep(priv->gpio_headphone,\n"
        "\t\t\t\t\t priv->headphone_gpio_follows_speaker ?\n"
        "\t\t\t\t\t priv->speaker_en : !priv->speaker_en);")
    source = detect_board(source)
    return replace_once(source, "\tINIT_LIST_HEAD(&priv->hdmi_pcm_list);",
        "\t/* Both active-low descriptors follow speaker power on this board. */\n"
        "\tpriv->headphone_gpio_follows_speaker =\n"
        '\t\tdmi_match(DMI_SYS_VENDOR, "Infinix") &&\n'
        '\t\tdmi_match(DMI_BOARD_NAME, "EM_IC325_200B_V1.0 20211012");\n\n'
        "\tINIT_LIST_HEAD(&priv->hdmi_pcm_list);")


def restart(source: str) -> str:
    return replace_once(source, "\tcase SNDRV_PCM_TRIGGER_RESUME:\n\t\tbreak;",
        "\tcase SNDRV_PCM_TRIGGER_RESUME:\n"
        "\t\t/* STOP can mute the amp without cycling DAPM speaker power. */\n"
        "\t\tif (priv->headphone_gpio_follows_speaker &&\n"
        "\t\t    substream->stream == SNDRV_PCM_STREAM_PLAYBACK &&\n"
        "\t\t    !priv->speaker_en)\n"
        "\t\t\tqueue_delayed_work(system_dfl_wq, &priv->pcm_pop_work,\n"
        "\t\t\t\t\t   msecs_to_jiffies(70));\n\t\tbreak;")


def patch(name: str, subject: str, body: str, before: str, after: str) -> None:
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                       fromfile="a/" + TARGET, tofile="b/" + TARGET))
    (ROOT / "patches" / name).write_text(
        f"Subject: [PATCH] {subject}\n\n{body}\n\n"
        "Research candidate; not submitted or hardware-qualified as a new release.\n\n"
        "---\n" + f"diff --git a/{TARGET} b/{TARGET}\n" + diff)


def main() -> None:
    upstream = (ROOT / "inputs/linux-upstream/sof_es8336.c").read_text()
    first = board_gpio(upstream)
    final = restart(first)
    patch("0001-inbook-x2-board-gpio.patch",
          "ASoC: Intel: sof_es8336: add Infinix EM_IC325 GPIO configuration",
          "Select both GPIOs for the exact Infinix board and make the secondary\n"
          "descriptor follow speaker power. Preserve the existing mapping order\n"
          "and module-parameter override. Other boards retain their polarity.\n"
          "Based on local GPIO/playback evidence and vendor configuration analysis.",
          upstream, first)
    patch("0002-inbook-x2-playback-restart.patch",
          "ASoC: Intel: sof_es8336: restore Infinix amplifier on playback restart",
          "STOP mutes the amplifier without changing the DAPM state. A subsequent\n"
          "START can therefore leave playback running with the amplifier muted.\n"
          "Requeue the existing 70 ms GPIO work for playback START, RESUME and\n"
          "PAUSE_RELEASE while the speaker route is powered. Limit to the tested\n"
          "board; capture and other boards are unchanged. This ports the previously\n"
          "hardware-tested local 1.0.1 fix to the pinned upstream source.\n"
          "Link: https://github.com/thesofproject/linux/issues/5967",
          first, final)
    module = ROOT / "module"
    module.mkdir(exist_ok=True)
    (module / "sof_es8336_modern.c").write_text(final)
    # Keep the already-built 6.18 compatibility implementation, adding autodetection.
    legacy = (ROOT / "inputs/linux-current/sof_es8336_legacy.c").read_text()
    legacy = detect_board(legacy)
    legacy = replace_once(legacy, 'MODULE_VERSION("1.0.1-infinix");', '')
    legacy = legacy.replace("Infinix ES8326 GPIO correction 1.0.1 enabled",
                            "Infinix ES8326 research GPIO correction enabled")
    (module / "sof_es8336_legacy.c").write_text(legacy)
    shutil.copy2(ROOT / "inputs/linux-current/hdac_hda.h", module)
    wrapper = (ROOT / "inputs/linux-current/sof_es8336.c").read_text()
    (module / "sof_es8336.c").write_text(wrapper + '\nMODULE_VERSION("1.1.0-research");\n')
    common = (ROOT / "inputs/linux-upstream/hda_dsp_common.h").read_text()
    common = replace_once(common, '"../../codecs/hdac_hda.h"', '"hdac_hda.h"')
    (module / "hda_dsp_common.h").write_text(common)
    (ROOT / "patches/series").write_text(
        "0001-inbook-x2-board-gpio.patch\n0002-inbook-x2-playback-restart.patch\n")
    print("Generated two patches and module sources; no live system changes.")


if __name__ == "__main__":
    main()
