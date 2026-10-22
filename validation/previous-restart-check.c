#include <alsa/asoundlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void check(int result, const char *operation) {
    if (result < 0) {
        fprintf(stderr, "%s: %s\n", operation, snd_strerror(result));
        exit(1);
    }
}

/* Capture control-pin state while silent PCM playback is active. */
static void snapshot(const char *label) {
    char line[512];
    printf("\n%s\n", label);
    FILE *f = fopen("/sys/kernel/debug/gpio", "r");
    if (f) {
        while (fgets(line, sizeof(line), f))
            if (strstr(line, "speakers-enable") || strstr(line, "headphone-enable"))
                fputs(line, stdout);
        fclose(f);
    }
    f = fopen("/proc/asound/card0/pcm0p/sub0/status", "r");
    if (f) {
        while (fgets(line, sizeof(line), f)) fputs(line, stdout);
        fclose(f);
    }
    fflush(stdout);
}

int main(void) {
    snd_pcm_t *pcm;
    static int32_t silence[48000 * 2];
    alarm(12);
    check(snd_pcm_open(&pcm, "hw:sofessx8336,0", SND_PCM_STREAM_PLAYBACK, 0), "open");
    check(snd_pcm_set_params(pcm, SND_PCM_FORMAT_S32_LE, SND_PCM_ACCESS_RW_INTERLEAVED,
                             2, 48000, 0, 1000000), "configure");
    snd_pcm_uframes_t buffer_size, period_size;
    check(snd_pcm_get_params(pcm, &buffer_size, &period_size), "buffer geometry");
    printf("buffer=%lu period=%lu\n", buffer_size, period_size);
    if (buffer_size > 48000) return 3;
    snd_pcm_sw_params_t *sw;
    snd_pcm_sw_params_alloca(&sw);
    check(snd_pcm_sw_params_current(pcm, sw), "get software parameters");
    check(snd_pcm_sw_params_set_start_threshold(pcm, sw, buffer_size), "start threshold");
    check(snd_pcm_sw_params(pcm, sw), "set software parameters");
    for (int i = 0; i < 4; ++i) {
        if (i) {
            check(snd_pcm_drop(pcm), "stop");
            check(snd_pcm_prepare(pcm), "prepare");
        }
        snd_pcm_sframes_t written = snd_pcm_writei(pcm, silence, buffer_size);
        check((int)written, "write silence");
        if (written != (snd_pcm_sframes_t)buffer_size) return 2;
        if (snd_pcm_state(pcm) == SND_PCM_STATE_PREPARED)
            check(snd_pcm_start(pcm), "start");
        usleep(150000);
        snd_pcm_sframes_t delay;
        int delay_result = snd_pcm_delay(pcm, &delay);
        snapshot(i ? "After stop/restart" : "Initial start");
        check(delay_result, "read delay");
        printf("delay=%ld\n", (long)delay);
    }
    check(snd_pcm_drop(pcm), "final stop");
    check(snd_pcm_close(pcm), "close");
    return 0;
}
