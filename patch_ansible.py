import os

filepath = "src/main/java/io/kestra/plugin/ansible/runner/AnsibleRunner.java"
with open(filepath, "r") as f:
    code = f.read()

# F10: Remove Max and Min imports
code = code.replace("import jakarta.validation.constraints.Max;\n", "")
code = code.replace("import jakarta.validation.constraints.Min;\n", "")

# F1 & N2: Static patterns
code = code.replace(
    'private static final java.util.regex.Pattern PKG_ALLOWLIST = java.util.regex.Pattern.compile("^[a-zA-Z0-9_.-]+$");',
    'private static final java.util.regex.Pattern PKG_ALLOWLIST = java.util.regex.Pattern.compile("^[a-zA-Z0-9_][a-zA-Z0-9_\\\\-\\\\.\\\\=\\\\>\\\\<\\\\~]*$");\n    private static final java.util.regex.Pattern WHITESPACE_PATTERN = java.util.regex.Pattern.compile(".*\\\\s.*");'
)

code = code.replace(
    'if (arg.matches(".*\\\\s.*") || arg.startsWith("-")) {',
    'if (WHITESPACE_PATTERN.matcher(arg).matches() || arg.startsWith("-")) {'
)

# F4: failOnErrors default description and default evaluation
code = code.replace(
    '@Schema(title = "Fail task if return code is non-zero (default false for programmatic downstream handling)")',
    '@Schema(title = "Fail task if return code is non-zero (default true)")'
)
code = code.replace(
    'boolean failTask = runContext.render(this.failOnErrors).as(Boolean.class).orElse(false);',
    'boolean failTask = runContext.render(this.failOnErrors).as(Boolean.class).orElse(true);'
)

# F2: Path traversal replacements
code = code.replace('Path localSource = workingDir.resolve(relSource);', 'Path localSource = secureResolve(workingDir, relSource);')
code = code.replace('Path localScript = workingDir.resolve(scriptStr.startsWith("/") ? scriptStr.substring(1) : scriptStr);', 'Path localScript = secureResolve(workingDir, scriptStr.startsWith("/") ? scriptStr.substring(1) : scriptStr);')
code = code.replace('Path localSrc = workingDir.resolve(src.startsWith("/") ? src.substring(1) : src);', 'Path localSrc = secureResolve(workingDir, src.startsWith("/") ? src.substring(1) : src);')
code = code.replace('Path localInv = workingDir.resolve(relInv);', 'Path localInv = secureResolve(workingDir, relInv);')
code = code.replace('Path localSubInv = workingDir.resolve("inventory").resolve(relInv);', 'Path localSubInv = secureResolve(workingDir.resolve("inventory"), relInv);')
code = code.replace('Path localPluralInv = workingDir.resolve("inventories").resolve(relInv);', 'Path localPluralInv = secureResolve(workingDir.resolve("inventories"), relInv);')
code = code.replace('Path candPath = workingDir.resolve(cand);', 'Path candPath = secureResolve(workingDir, cand);')

# F15: Spool file permissions
code = code.replace(
    'Path logSpoolFile = Files.createTempFile("ansible-runner-log-" + ident + "-", ".log");',
    '''Path logSpoolFile = Files.createTempFile("ansible-runner-log-" + ident + "-", ".log");
        try {
            Files.setPosixFilePermissions(logSpoolFile, PosixFilePermissions.fromString("rw-------"));
        } catch (UnsupportedOperationException ignored) {
            logSpoolFile.toFile().setReadable(true, true);
            logSpoolFile.toFile().setWritable(true, true);
        }'''
)

# F6: try/finally for cleanup wrapping execution phase
code = code.replace(
    '        Path runnerDir = workingDir.resolve("runner");',
    '        AnsibleRunnerLogConsumer logConsumer = null;\n        Path logSpoolFile = Files.createTempFile("ansible-runner-log-tmp-", ".log");\n        try {\n        Path runnerDir = workingDir.resolve("runner");'
)
# Fix the existing logSpoolFile creation since we moved it up.
code = code.replace(
    '''Path logSpoolFile = Files.createTempFile("ansible-runner-log-" + ident + "-", ".log");
        try {
            Files.setPosixFilePermissions(logSpoolFile, PosixFilePermissions.fromString("rw-------"));
        } catch (UnsupportedOperationException ignored) {
            logSpoolFile.toFile().setReadable(true, true);
            logSpoolFile.toFile().setWritable(true, true);
        }
        AnsibleRunnerLogConsumer logConsumer = new AnsibleRunnerLogConsumer(''',
    '''// Rename the tmp spool file now that we have the ident
        Path finalSpool = workingDir.resolve("ansible-runner-log-" + ident + "-" + System.currentTimeMillis() + ".log");
        Files.move(logSpoolFile, finalSpool, StandardCopyOption.REPLACE_EXISTING);
        logSpoolFile = finalSpool;
        try {
            Files.setPosixFilePermissions(logSpoolFile, PosixFilePermissions.fromString("rw-------"));
        } catch (UnsupportedOperationException ignored) {
            logSpoolFile.toFile().setReadable(true, true);
            logSpoolFile.toFile().setWritable(true, true);
        }
        logConsumer = new AnsibleRunnerLogConsumer('''
)

# Fix the nested try-catch around run()
code = code.replace(
    '''        ScriptOutput scriptOutput;
        try {
            scriptOutput = commandsWrapper.run();
        } catch (Exception e) {
            Files.deleteIfExists(logSpoolFile);
            throw e;
        } finally {
            logConsumer.close();
            FileUtils.deleteQuietly(envDir.toFile());
        }''',
    '''        ScriptOutput scriptOutput = commandsWrapper.run();'''
)

# And add the closing blocks at the end of run()
code = code.replace(
    '        return output;\n    }',
    '''        return output;
        } catch (Exception e) {
            try { Files.deleteIfExists(logSpoolFile); } catch (Exception ignored) {}
            throw e;
        } finally {
            if (logConsumer != null) logConsumer.close();
            FileUtils.deleteQuietly(workingDir.resolve("runner/env").toFile());
        }
    }'''
)

# N1: Delete commented out code
import re
code = re.sub(r'                            if \("runner_on_ok"\.equals\(event\) \|\|.*?// tasks\.add\(taskRecord\); // omitted from memory\n                                \}\n', '', code, flags=re.DOTALL)

# F3 & F18: Limit sizes
code = code.replace('List<String> failedHosts = new ArrayList<>();', 'Set<String> failedHostsSet = new java.util.LinkedHashSet<>();')
code = code.replace(
    'if (!host.isBlank() && !failedHosts.contains(host)) {\n                                    if (failedHosts.size() < 100) failedHosts.add(host);\n                                }',
    'if (!host.isBlank()) {\n                                    if (failedHostsSet.size() < 1000) failedHostsSet.add(host);\n                                }'
)
code = code.replace(
    'if ((failuresNode.path(h).asInt(0) > 0 || unreachableNode.path(h).asInt(0) > 0) && !failedHosts.contains(h)) {\n                                        if (failedHosts.size() < 100) failedHosts.add(h);\n                                    }',
    'if ((failuresNode.path(h).asInt(0) > 0 || unreachableNode.path(h).asInt(0) > 0)) {\n                                        if (failedHostsSet.size() < 1000) failedHostsSet.add(h);\n                                    }'
)
code = code.replace('failedTasks.add(failedTask);', 'if (failedTasks.size() < 1000) failedTasks.add(failedTask);')
code = code.replace(
    'return new ExecutionTelemetry(status, rc, failedHosts, stats, summaryBuilder.build(), failedTasks);',
    'return new ExecutionTelemetry(status, rc, new ArrayList<>(failedHostsSet), stats, summaryBuilder.build(), failedTasks);'
)

# F18: O(n^2) contains and unclosed Files.list
# Find unclosed Files.list(inventoryDir)
code = code.replace(
    'if (Files.list(inventoryDir).findAny().isPresent()) {',
    '''try (java.util.stream.Stream<Path> invStream = Files.list(inventoryDir)) {
                    if (invStream.findAny().isPresent()) {'''
)
code = code.replace(
    '''runContext.logger().info("Using auto-detected inventory directory: {}", inventoryFolder);
                    return;
                }
            } catch (Exception ignored) {}''',
    '''runContext.logger().info("Using auto-detected inventory directory: {}", inventoryFolder);
                        return;
                    }
                }
            } catch (Exception ignored) {}'''
)
code = code.replace(
    '''runContext.logger().info("Using auto-detected inventory directory: {}", inventoriesFolder);
                    return;
                }
            } catch (Exception ignored) {}''',
    '''runContext.logger().info("Using auto-detected inventory directory: {}", inventoriesFolder);
                        return;
                    }
                }
            } catch (Exception ignored) {}'''
)

# F7: Swallowed Exceptions
code = code.replace('FileUtils.copyDirectory(playbooksDir.toFile(), projectDir.toFile());\n            } catch (Exception ignored) {}', 'FileUtils.copyDirectory(playbooksDir.toFile(), projectDir.toFile());\n            } catch (Exception e) { runContext.logger().warn("Failed to copy playbooks dir: {}", e.getMessage()); }')
code = code.replace('catch (Exception ignored) {}', 'catch (Exception e) { runContext.logger().warn("Ignored exception: {}", e.getMessage()); }')
# Revert the ones that shouldn't be warned generically, let's fix the specific ones
code = code.replace('} catch (IOException e) { runContext.logger().warn("Ignored exception: {}", e.getMessage()); }', '} catch (IOException e) { throw new RuntimeException(e); }')

# Limit stats size
code = code.replace('stats.put(h, hStat);', 'if (stats.size() < 1000) stats.put(h, hStat);')

with open(filepath, "w") as f:
    f.write(code)
