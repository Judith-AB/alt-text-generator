import React, { useState } from 'react';
import {
    View,
    Text,
    Button,
    Image,
    ScrollView,
    ActivityIndicator,
    StyleSheet,
    TouchableOpacity,
    Alert, // Added for feedback
} from 'react-native';

import * as ImagePicker from 'expo-image-picker';
import * as Speech from 'expo-speech';
import * as Haptics from 'expo-haptics';
import * as Clipboard from 'expo-clipboard'; // Added for Copy functionality
import axios from 'axios';
import { API_BASE_URL } from './config';

export default function App() {
    const [image, setImage] = useState(null);
    const [altText, setAltText] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [mode, setMode] = useState('simple');

    const takePhoto = async () => {
        setError('');
        const result = await ImagePicker.launchCameraAsync({ quality: 1 });
        if (!result.canceled) {
            setImage(result.assets[0].uri);
            setAltText('');
        }
    };

    const pickFromGallery = async () => {
        setError('');
        const result = await ImagePicker.launchImageLibraryAsync({ quality: 1 });
        if (!result.canceled) {
            setImage(result.assets[0].uri);
            setAltText('');
        }
    };

    // --- New Copy Function ---
    const copyToClipboard = async () => {
        await Clipboard.setStringAsync(altText);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        Alert.alert('Copied!', 'Alt-text copied to clipboard.');
    };

    const generateAltText = async () => {
        if (!image) return;

        setLoading(true);
        setAltText('');
        setError('');
        
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

        const formData = new FormData();
        formData.append('image', {
            uri: image,
            name: 'photo.jpg',
            type: 'image/jpeg',
        });
        formData.append('mode', mode); 

        try {
            const res = await axios.post(
                `${API_BASE_URL}/api/generate-alt-text/`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );

            setAltText(res.data.alt_text);
            Speech.speak(res.data.alt_text);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        } catch (e) {
            setError('Unable to generate description. Please try again.');
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <ScrollView contentContainerStyle={styles.container}>
            <Text style={styles.title} accessibilityRole="header">Alt Text Generator</Text>

            <Text style={styles.subtitle}>
                Generate spoken descriptions to support accessibility.
            </Text>

            <View style={styles.buttonGroup}>
                <Button 
                    title="Take Photo" 
                    onPress={takePhoto} 
                    accessibilityLabel="Open camera to take a photo"
                />
            </View>

            <View style={styles.buttonGroup}>
                <Button 
                    title="Choose from Gallery" 
                    onPress={pickFromGallery} 
                    accessibilityLabel="Open gallery to choose an image"
                />
            </View>

            {image && (
                <View style={styles.modeContainer}>
                    <Text style={styles.modeTitle}>Select Description Complexity:</Text>
                    <View style={styles.modeSelector}>
                        {['simple', 'detailed', 'functional'].map((m) => (
                            <TouchableOpacity
                                key={m}
                                style={[styles.modeButton, mode === m && styles.modeButtonSelected]}
                                onPress={() => {
                                    setMode(m);
                                    Haptics.selectionAsync();
                                }}
                                accessibilityRole="radio"
                                accessibilityState={{ selected: mode === m }}
                            >
                                <Text style={[styles.modeText, mode === m && styles.modeTextSelected]}>
                                    {m.charAt(0).toUpperCase() + m.slice(1)}
                                </Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                </View>
            )}

            {image && <Image source={{ uri: image }} style={styles.image} accessibilityLabel="Selected image for processing" />}

            {image && !loading && (
                <View style={styles.buttonGroup}>
                    <Button 
                        title={`Generate ${mode} Description`} 
                        onPress={generateAltText} 
                        color="#2196F3"
                    />
                </View>
            )}

            {loading && (
                <View style={styles.loading}>
                    <ActivityIndicator size="large" color="#2196F3" />
                    <Text>Analyzing image for {mode} details...</Text>
                </View>
            )}

            {altText !== '' && (
                <View style={styles.resultContainer}>
                    <Text style={styles.resultHeader}>Generated Alt-Text:</Text>
                    <Text style={styles.result}>{altText}</Text>
                    
                    <View style={styles.actionRow}>
                        <View style={styles.flexButton}>
                            <Button title="Speak Again" onPress={() => Speech.speak(altText)} />
                        </View>
                        <View style={styles.flexButton}>
                            <Button title="Copy Text" color="#4CAF50" onPress={copyToClipboard} />
                        </View>
                    </View>
                </View>
            )}

            {error !== '' && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { padding: 20, backgroundColor: '#fff' },
    title: { fontSize: 28, fontWeight: 'bold', marginBottom: 10, textAlign: 'center' },
    subtitle: { fontSize: 16, marginBottom: 20, textAlign: 'center', color: '#666' },
    buttonGroup: { marginBottom: 15 },
    modeContainer: { marginVertical: 15, padding: 10, backgroundColor: '#f9f9f9', borderRadius: 8 },
    modeTitle: { fontSize: 16, fontWeight: '600', marginBottom: 10 },
    modeSelector: { flexDirection: 'row', justifyContent: 'space-between' },
    modeButton: { 
        paddingVertical: 8, 
        paddingHorizontal: 12, 
        borderRadius: 20, 
        borderWidth: 1, 
        borderColor: '#ddd' 
    },
    modeButtonSelected: { backgroundColor: '#2196F3', borderColor: '#2196F3' },
    modeText: { fontSize: 14, color: '#333' },
    modeTextSelected: { color: '#fff', fontWeight: 'bold' },
    image: { width: 300, height: 300, marginVertical: 20, alignSelf: 'center', borderRadius: 10 },
    loading: { marginTop: 20, alignItems: 'center' },
    resultContainer: { marginTop: 20, padding: 15, backgroundColor: '#e3f2fd', borderRadius: 8 },
    resultHeader: { fontWeight: 'bold', color: '#1976D2', marginBottom: 5 },
    result: { fontSize: 18, color: '#333', marginBottom: 15 },
    // New styles for the button row
    actionRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 10 },
    flexButton: { flex: 1 },
    error: { color: 'red', marginTop: 20, textAlign: 'center' },
});