import re
import sys

with open("src/main/java/io/kestra/plugin/ansible/runner/AnsibleRunner.java", "r") as f:
    content = f.read()

# F18: O(n^2) contains and unclosed Files.list
# Find unclosed Files.list(inventoryDir)
content = content.replace(
    'if (Files.list(inventoryDir).findAny().isPresent()) {',
    '''try (java.util.stream.Stream<Path> invStream = Files.list(inventoryDir)) {
                    if (invStream.findAny().isPresent()) {'''
)
# add closing braces for the tries
content = content.replace(
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

content = content.replace(
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

# N1: Delete commented out code
content = re.sub(r'                            if \("runner_on_ok"\.equals\(event\) \|\|.*?// tasks\.add\(taskRecord\); // omitted from memory\n                                \}\n', '', content, flags=re.DOTALL)

# F3 & F18: O(n^2) and failedHosts capped at 100 silently. Let's make it a Set and then limit tasks.
content = content.replace(
    'List<String> failedHosts = new ArrayList<>();',
    'Set<String> failedHostsSet = new LinkedHashSet<>();'
)
content = content.replace(
    'if (!host.isBlank() && !failedHosts.contains(host)) {\n                                    if (failedHosts.size() < 100) failedHosts.add(host);\n                                }',
    'if (!host.isBlank()) {\n                                    if (failedHostsSet.size() < 1000) failedHostsSet.add(host);\n                                }'
)
content = content.replace(
    'if ((failuresNode.path(h).asInt(0) > 0 || unreachableNode.path(h).asInt(0) > 0) && !failedHosts.contains(h)) {\n                                        if (failedHosts.size() < 100) failedHosts.add(h);\n                                    }',
    'if ((failuresNode.path(h).asInt(0) > 0 || unreachableNode.path(h).asInt(0) > 0)) {\n                                        if (failedHostsSet.size() < 1000) failedHostsSet.add(h);\n                                    }'
)
content = content.replace(
    'failedTasks.add(failedTask);',
    'if (failedTasks.size() < 1000) failedTasks.add(failedTask);'
)
content = content.replace(
    'return new ExecutionTelemetry(status, rc, failedHosts, stats, summaryBuilder.build(), failedTasks);',
    'return new ExecutionTelemetry(status, rc, new ArrayList<>(failedHostsSet), stats, summaryBuilder.build(), failedTasks);'
)

# F7: Fix swallowed exceptions
content = content.replace(
    '} catch (IOException ignored) {}',
    '} catch (IOException e) { throw new RuntimeException("Failed to make script executable", e); }'
)
content = content.replace(
    '} catch (Exception ignored) {}',
    '} catch (Exception e) { throw new RuntimeException("Error processing ansible files", e); }'
)
# Wait, some ignored are legitimate, like the ones in JSON parsing of the playbook inline. 
# It's better to log them. Let me undo that generic replace.
