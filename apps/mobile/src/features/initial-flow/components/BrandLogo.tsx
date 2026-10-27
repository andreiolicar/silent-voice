import {
  Image,
  StyleSheet,
  type ImageStyle,
  type StyleProp,
} from 'react-native';

type BrandLogoProps = {
  large?: boolean;
  style?: StyleProp<ImageStyle>;
};

export function BrandLogo({ large = false, style }: BrandLogoProps) {
  return (
    <Image
      accessibilityLabel="Silent Voice"
      resizeMode="contain"
      source={require('@/assets/images/initial-flow/logo-full.png')}
      style={[large ? styles.large : styles.default, style]}
    />
  );
}

const styles = StyleSheet.create({
  default: { width: 162, height: 34 },
  large: { width: 222, height: 47 },
});
