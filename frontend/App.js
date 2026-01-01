import React, { useState } from 'react';
import {
    View,
    Text,
    Button,
    Image,
    ScrollView,
    ActivityIndicator,
    StyleSheet,
} from 'react-native';

import * as ImagePicker from 'expo-image-picker';
import * as Speech from 'expo-speech';
import axios from 'axios';
import { API_BASE_URL } from './config';

export default function App() {
    const [image, setImage] = useState(null);
    const [altText, setAltText] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

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

    const generateAltText = async () => {
        if (!image) return;

        setLoading(true);
        setAltText('');
        setError('');

        const formData = new FormData();
        formData.append('image', {
            uri: image,
            name: 'photo.jpg',
            type: 'image/jpeg',
        });

        try {
            const res = await axios.post(
                `${API_BASE_URL}/api/generate-alt-text/`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );

            setAltText(res.data.alt_text);
            Speech.speak(res.data.alt_text);
        } catch (e) {
            setError('Unable to generate description. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <ScrollView contentContainerStyle={styles.container}>
            <Text style={styles.title}>Alt Text Generator</Text>

            <Text style={styles.subtitle}>
                Generate spoken descriptions for images to support accessibility.
            </Text>

            <Text style={styles.instructions}>
                Take a photo or choose an image. The app will describe it aloud.
            </Text>

            <View style={styles.buttonGroup}>
                <Button title="Take Photo" onPress={takePhoto} />
            </View>

            <View style={styles.buttonGroup}>
                <Button title="Choose from Gallery" onPress={pickFromGallery} />
            </View>

            {image && <Image source={{ uri: image }} style={styles.image} />}

            {image && !loading && (
                <View style={styles.buttonGroup}>
                    <Button title="Generate Description" onPress={generateAltText} />
                </View>
            )}

            {loading && (
                <View style={styles.loading}>
                    <ActivityIndicator size="large" />
                    <Text>Generating description...</Text>
                </View>
            )}

            {altText !== '' && <Text style={styles.result}>{altText}</Text>}

            {error !== '' && <Text style={styles.error}>{error}</Text>}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { padding: 20 },
    title: { fontSize: 26, fontWeight: 'bold', marginBottom: 10 },
    subtitle: { fontSize: 16, marginBottom: 10 },
    instructions: { fontSize: 14, marginBottom: 20, color: '#555' },
    buttonGroup: { marginBottom: 10 },
    image: {
        width: 300,
        height: 300,
        marginVertical: 20,
        alignSelf: 'center',
    },
    loading: { marginTop: 20, alignItems: 'center' },
    result: { fontSize: 18, marginTop: 20, fontWeight: '500' },
    error: { color: 'red', marginTop: 20 },
});
