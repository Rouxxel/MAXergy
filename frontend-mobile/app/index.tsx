import { StatusBar } from 'expo-status-bar';
import { Text, View } from 'react-native';

export default function Index() {
  return (
    <View className="flex-1 bg-background justify-center items-center p-6">
      <View className="bg-card p-6 rounded-lg border border-border items-center">
        <Text className="text-primary text-3xl font-bold mb-2">MAXergy Mobile</Text>
        <Text className="text-foreground text-center mb-4">
          Tailwind CSS & NativeWind Setup is Working!
        </Text>
        <View className="bg-secondary px-4 py-2 rounded-md">
          <Text className="text-secondary-foreground font-semibold">Test Tailwind Styles</Text>
        </View>
      </View>
      <StatusBar style="light" />
    </View>
  );
}
