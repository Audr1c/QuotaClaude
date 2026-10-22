/* Tiny launcher: starts the run script that sits next to it, in a terminal, and passes the arguments along.
 *   Windows: runs run.bat      Linux/macOS: runs run.sh
 * Build: see the Makefile (zig cc cross-compiles both from any OS). */
#ifdef _WIN32
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

int wmain(int argc, wchar_t **argv) {
    wchar_t exe[MAX_PATH * 2], cmd[MAX_PATH * 4 + 2048];
    DWORD n = GetModuleFileNameW(NULL, exe, MAX_PATH * 2);
    if (n == 0 || n >= MAX_PATH * 2) return 1;
    wchar_t *slash = wcsrchr(exe, L'\\');
    if (!slash) return 1;
    *slash = 0;                                            /* exe now holds the folder */
    /* look for run.bat next to the exe, then one folder up (when the exe lives in bin\) */
    wchar_t bat[MAX_PATH * 2];
    swprintf(bat, MAX_PATH * 2, L"%ls\\run.bat", exe);
    if (GetFileAttributesW(bat) == INVALID_FILE_ATTRIBUTES) swprintf(bat, MAX_PATH * 2, L"%ls\\..\\run.bat", exe);
    if (GetFileAttributesW(bat) == INVALID_FILE_ATTRIBUTES) {
        fprintf(stderr, "run.bat not found next to this program.\n");
        system("pause");
        return 1;
    }
    int len = swprintf(cmd, sizeof cmd / sizeof *cmd, L"cmd.exe /c \"\"%ls\"", bat);
    for (int i = 1; i < argc && len < (int)(sizeof cmd / sizeof *cmd) - 300; i++)
        len += swprintf(cmd + len, sizeof cmd / sizeof *cmd - len, L" \"%ls\"", argv[i]);
    wcscat(cmd, L"\"");
    STARTUPINFOW si = { sizeof si };
    PROCESS_INFORMATION pi;
    if (!CreateProcessW(NULL, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) return 1;
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);
    return (int)code;
}
#else
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    char exe[PATH_MAX], script[PATH_MAX + 16];
    ssize_t n = readlink("/proc/self/exe", exe, sizeof exe - 1);
    if (n <= 0) { fprintf(stderr, "cannot locate myself\n"); return 1; }
    exe[n] = 0;
    char *slash = strrchr(exe, '/');
    if (!slash) return 1;
    *slash = 0;
    snprintf(script, sizeof script, "%s/run.sh", exe);
    if (access(script, R_OK) != 0) snprintf(script, sizeof script, "%s/../run.sh", exe);
    if (access(script, R_OK) != 0) { fprintf(stderr, "run.sh not found next to this program.\n"); return 1; }
    char *args[argc + 2];
    args[0] = "sh"; args[1] = script;
    for (int i = 1; i < argc; i++) args[i + 1] = argv[i];
    args[argc + 1] = NULL;
    execv("/bin/sh", args);
    perror("exec");
    return 1;
}
#endif
