import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';

// Mockable keypoint input interface
// props.keypointStream should provide { x, y, confidence } in [0,1]
export default function NeuroMiniGame({ keypointStream, apiEndpoint }) {
  const [score, setScore] = useState(0);
  const [target, setTarget] = useState({ x: 0.7, y: 0.5, r: 0.1 });
  const [hits, setHits] = useState(0);
  const lastPoint = useRef({ x: 0.5, y: 0.5, confidence: 0 });

  useEffect(() => {
    const sub = keypointStream?.subscribe?.((pt) => {
      lastPoint.current = pt;
      const dx = pt.x - target.x;
      const dy = pt.y - target.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (pt.confidence > 0.5 && dist < target.r) {
        setScore((s) => s + 1);
        setHits((h) => h + 1);
        // new target
        setTarget({ x: Math.random(), y: Math.random(), r: 0.08 + Math.random() * 0.08 });
      }
    });
    return () => sub?.unsubscribe?.();
  }, [keypointStream, target]);

  const uploadScore = async () => {
    if (!apiEndpoint) return;
    await fetch(apiEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score, hits, ts: Date.now() }),
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Neuro Mini Game</Text>
      <View style={styles.gameArea}>
        <View
          style={[
            styles.target,
            { left: `${target.x * 100}%`, top: `${target.y * 100}%`, width: `${target.r * 200}%`, height: `${target.r * 200}%` },
          ]}
        />
        <View
          style={[
            styles.cursor,
            { left: `${lastPoint.current.x * 100}%`, top: `${lastPoint.current.y * 100}%` },
          ]}
        />
      </View>
      <Text style={styles.score}>Score: {score}</Text>
      <TouchableOpacity style={styles.button} onPress={uploadScore}>
        <Text style={styles.buttonText}>Upload Score</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#111' },
  title: { color: '#fff', fontSize: 20, marginBottom: 12 },
  gameArea: { flex: 1, backgroundColor: '#222', borderRadius: 12, position: 'relative' },
  target: { position: 'absolute', backgroundColor: '#0f0', borderRadius: 999 },
  cursor: { position: 'absolute', width: 12, height: 12, backgroundColor: '#fff', borderRadius: 6 },
  score: { color: '#fff', marginTop: 12 },
  button: { marginTop: 10, padding: 12, backgroundColor: '#444', borderRadius: 8 },
  buttonText: { color: '#fff', textAlign: 'center' },
});
