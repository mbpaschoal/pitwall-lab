# Verification after the reported reboot

English · [Português](README.md)

Created by: MBPaschoal
Status: post-reboot public acceptance failed
Type: deployment verification

The owner replied “Feito” to the administrative reboot request. The [confirmation record](context.json) records when this was noted, without inventing an exact reboot time. No code, data or package was changed while checking **0.8.28**.

**Result: 0/4 contexts passed**, PT/EN at 1440/390 px, with bounded attempts. One opening showed the version and Mexico photograph while controls remained incomplete; that is not acceptance. [Consolidated result and hashes](post-reboot-result.json), [all attempts](publication.json), [incomplete-controls screenshot](1440-pt-1-failed.jpg).

A focused How it works session reached Python state `notRunning` while native controls remained placeholders, then displayed `Failed to fetch dynamically imported module`. Native JavaScript/font requests under `/~/+/static/` returned **500 and HTML**. [Console, responses and DOM samples](focused-diagnostic.json), [screenshot](focused-method.jpg), [diagnostic script](focused-diagnostic.cjs).

Later direct checks of two sampled JavaScript files returned 200/application-javascript. Bytes with and without a query parameter matched the pinned Streamlit 1.50.0 installation. This does not prove successful browser imports or establish the intermittent failure's cause. [Direct responses](native-resource-probe.json), [correct comparison](pinned-native-comparison.json). An initial local lookup omitted one `static` directory; it remains preserved as an invalid attempt, not evidence of absent files.

An isolated HTTP/1 comparison also failed: the main native module returned 500 and the application did not initialize. This connection change did not resolve the problem. [HTTP/1 diagnostic](http1-diagnostic/focused-diagnostic.json), [script](http1-diagnostic.cjs).

An [issue in the official Streamlit repository](https://github.com/streamlit/streamlit/issues/10510) describes a similar error without a confirmed reproduction or established fix there. [Preserved lookup](streamlit-issue-10510.json). It does not prove that Pitwall has the same cause.

The owner was asked whether controls work in their browser, distinguishing their experience from automated observations. Root cause remains open. Further diagnosis requires authenticated hosting logs, unavailable in the public session. Repeating reboots or changing dependencies without additional evidence is not recommended. Earlier failures remain preserved in the [delivery report](../README.en.md).
